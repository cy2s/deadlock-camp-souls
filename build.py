"""Build a full-camp Souls reference layer for Deadlock's Tab minimap."""

import argparse
import hashlib
import json
import math
import struct
import zlib
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
STOCK_LAYOUT_URL = (
    "https://raw.githubusercontent.com/SteamTracking/GameTracking-Deadlock/"
    "77b862290ad3050cafd2e9c3f47e0532e9d6dcfd/game/citadel/pak01_dir/"
    "panorama/layout/hud_minimap.xml"
)
CAMP_COLORS = ("Small", "Medium", "Large", "Sinner")
MAP_SIZE = 360
LABEL_WIDTH = 28  # Reserve the four-digit footprint even when the pill is narrower.
LABEL_HEIGHT = 14


def place_camps(camps: list[dict]) -> list[tuple[float, float, float, float]]:
    """Place readable labels around their exact anchors on the stock Tab map."""
    anchors = [(camp["x"] * MAP_SIZE, camp["y"] * MAP_SIZE) for camp in camps]
    offsets = sorted(
        ((x, y) for x in range(-32, 33, 2) for y in range(-32, 33, 2) if x or y),
        key=lambda point: (math.hypot(*point), abs(point[0]), point[1], point[0]),
    )
    # Place the densest clusters first, before labels from open areas use their nearby slots.
    placement_order = sorted(range(len(anchors)), key=lambda index: sum(
        sorted(math.dist(anchors[index], other) for other in anchors)[:6]
    ))
    positions = {}
    half_width = LABEL_WIDTH / 2
    half_height = LABEL_HEIGHT / 2
    for index in placement_order:
        x, y = anchors[index]
        for dx, dy in offsets:
            lx, ly = x + dx, y + dy
            if not (half_width + 1 <= lx <= MAP_SIZE - half_width - 1 and 22 <= ly <= MAP_SIZE - 22):
                continue
            if any(abs(lx - ax) < half_width + 3 and abs(ly - ay) < half_height + 3 for ax, ay in anchors):
                continue
            if any(abs(lx - bx) < LABEL_WIDTH + 1 and abs(ly - by) < LABEL_HEIGHT + 1
                   for _, _, bx, by in positions.values()):
                continue
            positions[index] = x, y, lx, ly
            break
        else:
            raise ValueError(f"No room for the label at {camps[index]['id']}")
    return [positions[index] for index in range(len(anchors))]


def position(x: float, y: float) -> str:
    return f"position: {100 * x / MAP_SIZE:.4f}% {100 * y / MAP_SIZE:.4f}% 0px;"


def patch_minimap(stock_layout: str, camps: list[dict], *, hover_only: bool = False) -> str:
    root = ET.fromstring(stock_layout)
    styles = root.find("styles")
    minimap = root.find("./Panel[@class='HudMinimap']")
    if styles is None or minimap is None or minimap.find("./Panel[@id='MinimapBackgroundTest']") is None:
        raise ValueError("The stock minimap layout has changed. Recheck the label layer's anchor.")

    ET.SubElement(styles, "include", {"src": "s2r://panorama/styles/camp_souls.vcss"})
    scripts = root.find("scripts")
    if scripts is None:
        scripts = ET.Element("scripts")
        root.insert(list(root).index(styles) + 1, scripts)
    ET.SubElement(scripts, "include", {"src": "s2r://panorama/scripts/camp_souls.vts"})
    overlay = ET.SubElement(minimap, "Panel", {"id": "CampSoulTotals", "hittest": "false", "hittestchildren": "false"})
    if not hover_only:
        ET.SubElement(overlay, "Label", {"id": "CampSoulLegend", "text": "Full camp · Est. Souls"})
    for camp, (x, y, lx, ly) in zip(camps, place_camps(camps), strict=True):
        counts = camp["counts"]
        color_class = next(color for color, count in zip(reversed(CAMP_COLORS), reversed(counts)) if count)
        distance = math.hypot(lx - x, ly - y)
        site = ET.SubElement(overlay, "Panel", {"id": camp["id"], "class": "CampSoulSite"})
        if distance > 14:
            angle = math.degrees(math.atan2(ly - y, lx - x))
            length = 100 * distance / MAP_SIZE
            ET.SubElement(site, "Panel", {
                "class": "CampSoulLink",
                "style": position((x + lx) / 2, (y + ly) / 2)
                + f" width: {length:.4f}%; transform: translateX(-50%) rotateZ({angle:.2f}deg);",
            })
        ET.SubElement(site, "Label", {
            "class": f"CampSoulLabel {color_class}", "style": position(lx, ly),
        })
    ET.SubElement(minimap, "Label", {"id": "CrateSoulValue", "hittest": "false"})
    ET.indent(root, space="\t")
    return ET.tostring(root, encoding="unicode") + "\n"


def compile_panorama(text: str, *, script: bool = False) -> bytes:
    """Encode a Panorama DATA resource. Scripts contain raw text in version 2."""
    source = text.encode("utf-8")
    payload = source if script else struct.pack("<IH", zlib.crc32(source), 0) + source
    version = 2 if script else 3
    header = struct.pack("<IHHII4sII", 32 + len(payload), 12, version, 8, 1, b"DATA", 12, len(payload))
    return header + bytes(4) + payload


def pack_vpk(resources: dict[str, bytes]) -> bytes:
    """Pack compiled resources into one VPK v2 directory archive."""
    groups = defaultdict(lambda: defaultdict(list))
    for name, data in sorted(resources.items()):
        path = PurePosixPath(name)
        groups[path.suffix[1:]][path.parent.as_posix()].append((path.stem, data))
    entries = bytearray()
    payload = bytearray()
    for extension, directories in groups.items():
        entries.extend(extension.encode("ascii") + b"\0")
        for directory, files in directories.items():
            entries.extend(directory.encode("ascii") + b"\0")
            for name, data in files:
                entries.extend(name.encode("ascii") + b"\0")
                entries.extend(struct.pack(
                    "<IHHIIH", zlib.crc32(data), 0, 0x7FFF, len(payload), len(data), 0xFFFF,
                ))
                payload.extend(data)
            entries.extend(b"\0")
        entries.extend(b"\0")
    entries.extend(b"\0")
    # Archive MD5 records cover consecutive 1 MiB ranges of embedded data.
    hashes = bytearray()
    chunk_size = 1024 * 1024
    for offset in range(0, len(payload), chunk_size):
        chunk = payload[offset:offset + chunk_size]
        hashes.extend(struct.pack("<III", 0x7FFF, offset, len(chunk)))
        hashes.extend(hashlib.md5(chunk).digest())

    header = struct.pack("<7I", 0x55AA1234, 2, len(entries), len(payload), len(hashes), 48, 0)
    archive = header + entries + payload + hashes
    archive += hashlib.md5(entries).digest() + hashlib.md5(hashes).digest()
    return archive + hashlib.md5(archive).digest()


def build(output: Path, stock_layout: str, *, hover_only: bool = False) -> None:
    camps = json.loads((ROOT / "camps.json").read_text(encoding="utf-8"))
    css = (ROOT / "camp_souls.css").read_text(encoding="utf-8")
    script = (ROOT / "camp_souls.js").read_text(encoding="utf-8")
    camp_data = [{key: camp[key] for key in ("id", "x", "y", "counts")} for camp in camps]
    script = script.replace("/* CAMP_DATA */ []", json.dumps(camp_data, separators=(",", ":")), 1)
    script = script.replace("/* HOVER_ONLY */ false", json.dumps(hover_only), 1)
    archive = pack_vpk({
        "panorama/layout/hud_minimap.vxml_c": compile_panorama(patch_minimap(stock_layout, camps, hover_only=hover_only)),
        "panorama/styles/camp_souls.vcss_c": compile_panorama(css),
        "panorama/scripts/camp_souls.vts_c": compile_panorama(script, script=True),
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(archive)
    print(f"{output} ({len(camps)} camps)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Destination VPK path")
    parser.add_argument("--hover-only", action="store_true", help="Show only the hovered camp while the Tab map is open")
    parser.add_argument("--minimap-layout", type=Path, help="Decompiled HUD minimap XML from client build 6871")
    args = parser.parse_args()
    if args.minimap_layout:
        layout = args.minimap_layout.read_text(encoding="utf-8")
    else:
        with urlopen(STOCK_LAYOUT_URL, timeout=20) as response:
            layout = response.read().decode("utf-8")
    default_output = ROOT / "dist"
    if args.hover_only:
        default_output /= "hover"
    build(args.output or default_output / "pak99_dir.vpk", layout, hover_only=args.hover_only)
