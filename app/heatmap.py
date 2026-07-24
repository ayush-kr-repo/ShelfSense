import matplotlib
matplotlib.use("Agg")                 # no GUI — we're on a server
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import cm

BOX_W, BOX_H = 140, 180               # fixed draw size per shelf (px)


def generate_heatmap(wh, out_path):
    """Draw each shelf as a box colored by occupancy (green=empty → red=full)."""
    dark = "#0f172a"
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(dark)
    ax.set_facecolor(dark)

    if not wh.shelves:
        ax.text(0.5, 0.5, "No shelves detected", color="#94a3b8",
                ha="center", va="center", fontsize=14, transform=ax.transAxes)
    else:
        xs, ys = [], []
        for s in wh.shelves:
            x, y = s.pixel_position.x, s.pixel_position.y
            color = cm.RdYlGn_r(s.occupancy_pct)         # 0→green, 1→red
            ax.add_patch(Rectangle((x, y), BOX_W, BOX_H, facecolor=color,
                                   edgecolor="white", linewidth=1.5, alpha=0.9))
            ax.text(x + BOX_W / 2, y + BOX_H / 2, f"{int(s.occupancy_pct * 100)}%",
                    ha="center", va="center", fontsize=11, fontweight="bold", color="black")
            xs += [x, x + BOX_W]; ys += [y, y + BOX_H]
        ax.set_xlim(min(xs) - 60, max(xs) + 60)
        ax.set_ylim(max(ys) + 60, min(ys) - 60)          # invert Y (image coords)

        sm = cm.ScalarMappable(cmap="RdYlGn_r"); sm.set_array([0, 1])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Occupancy", color="white")
        cbar.ax.tick_params(colors="white")

    ax.set_title("Shelf Occupancy Heatmap", color="white", fontsize=15, pad=12)
    ax.axis("off")
    fig.savefig(out_path, facecolor=dark, bbox_inches="tight", dpi=100)
    plt.close(fig)
