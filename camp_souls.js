(() => {
    "use strict";

    const camps = /* CAMP_DATA */ [];
    const hoverOnly = /* HOVER_ONLY */ false;
    const neutralClasses = ["neutral_weak", "neutral_medium", "neutral_large", "neutral_vault"];
    const baseRewards = [43, 71, 189, 310];
    const map = $.GetContextPanel();
    let overlay;
    let sites = [];

    function matchMinute() {
        let hud = map;
        while (hud && hud.id !== "Hud" && hud.paneltype !== "CitadelHud") hud = hud.GetParent();
        const bar = hud && hud.FindChildTraverse("TopBar");
        const time = bar && bar.FindChildTraverse("GameTime");
        const match = time && /^\s*(\d+):[0-5]\d\s*$/.exec(time.text);
        return match ? Number(match[1]) : null;
    }

    function campValue(counts, minute) {
        const scale = 1 + 0.0108 * minute;
        return counts.reduce((total, count, tier) => {
            const scaled = baseRewards[tier] * scale;
            const reward = tier === 3 ? Math.round(scaled) : Math.floor(scaled);
            return total + count * reward;
        }, 0);
    }

    function markerPosition(marker) {
        const position = /^\s*([\d.]+)%\s+([\d.]+)%/.exec(String(marker.style.position || ""));
        if (position) return [Number(position[1]) / 100, Number(position[2]) / 100];
        // Offsets are relative to the renderer, so they stay in map space when the view flips.
        if (marker.GetParent() !== map || map.actuallayoutwidth <= 0 || map.actuallayoutheight <= 0) return null;
        return [
            (marker.actualxoffset + marker.actuallayoutwidth / 2) / map.actuallayoutwidth,
            (marker.actualyoffset + marker.actuallayoutheight / 2) / map.actuallayoutheight,
        ];
    }

    function activeSites() {
        const active = new Set();
        for (const marker of map.Children()) {
            if (!marker.visible || !marker.BHasClass("map_button") || !marker.BHasClass("neutral")
                || !marker.BHasClass("active")) continue;
            if (hoverOnly && (typeof marker.BHasHoverStyle !== "function" || !marker.BHasHoverStyle())) continue;
            const type = neutralClasses.findIndex(name => marker.BHasClass(name));
            const position = markerPosition(marker);
            if (type < 0 || !position || !position.every(Number.isFinite)) continue;
            const [x, y] = position;
            const candidates = sites.filter(({ camp, type: siteType }) => siteType === type &&
                Math.hypot(camp.x - x, camp.y - y) <= 0.01);
            if (candidates.length === 1) active.add(candidates[0]);
        }
        if (hoverOnly && active.size > 1) active.clear();
        return active;
    }

    function refresh() {
        if (!map.IsValid()) return;
        const layer = map.FindChildTraverse("CampSoulTotals");
        if (layer && layer !== overlay) {
            overlay = layer;
            sites = camps.map(camp => {
                const panel = overlay.FindChildTraverse(camp.id);
                if (!panel) return null;
                const label = panel.FindChildrenWithClassTraverse("CampSoulLabel")[0];
                let type = camp.counts.length - 1;
                while (type >= 0 && !camp.counts[type]) type--;
                return label ? { camp, panel, label, type } : null;
            }).filter(Boolean);
        }
        const mapOpen = layer && map.BHasClass("dl_midtown") && map.BHasClass("gScoreboardOpen");
        if (mapOpen) {
            const minute = matchMinute();
            const active = minute === null ? new Set() : activeSites();
            for (const site of sites) {
                const observed = active.has(site);
                site.panel.SetHasClass("IsObserved", observed);
                if (observed) {
                    const value = String(campValue(site.camp.counts, minute));
                    if (site.label.text !== value) {
                        site.label.SetHasClass("WideValue", value.length >= 4);
                        site.label.text = value;
                    }
                }
            }
            layer.SetHasClass("HasCampSouls", active.size > 0);
        } else if (layer) {
            layer.SetHasClass("HasCampSouls", false);
        }
        $.Schedule(hoverOnly && mapOpen ? 0.05 : 0.25, refresh);
    }

    $.Schedule(0, refresh);
})();
