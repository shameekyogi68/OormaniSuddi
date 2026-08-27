"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Campaign Poster Renderer
=========================================
Renders high-impact citizen journalism campaign posters for @OormaniSuddi:
1. 4:5 Feed Post (1080x1350)
2. 9:16 Story / Status (1080x1920)
3. 1:1 Square Post (1080x1080)
"""
import os
import sys

from PIL import Image, ImageDraw

from brand import typo, components as cp
from brand.surface import (
    Surface, scrim, rule, vrule, panel, place_photo, grain,
    radial_glow, paste_logo, gilded_rule, cover
)
from brand.tokens import (
    C, Role, T, Grid, fmt, category, alpha, Grade, Brand
)

OUT_DIR = os.path.join(os.path.dirname(__file__), 'out', 'campaign')
os.makedirs(OUT_DIR, exist_ok=True)


def render_campaign_post_4x5(out_path: str):
    """Render 4:5 (1080x1350) Instagram Feed Post."""
    W, H = 1080, 1350
    sf = Surface(W, H, ss=2)
    m = Grid.margin
    cw = W - 2 * m

    # 1. Base dark background with warm horizon glow
    cp.page_base(sf, 0.6)
    radial_glow(sf, W * 0.5, H * 0.45, W * 0.75, C.gold_600, 0.15)
    cp.horizon(sf, H * 0.44, 1.0)

    # 2. Masthead at top
    top = cp.masthead(
        sf, m, 56, cw,
        right_top='ವಿಶೇಷ ಅಭಿಯಾನ',
        right_bot='ಕರಾವಳಿ ಜನಧ್ವನಿ'
    ) + 40

    # 3. Eyebrow / Campaign Tag
    rail_h = 32
    sf.draw.rectangle(
        [sf.s(m), sf.s(top), sf.s(m + Grid.rail) - 1, sf.s(top + rail_h) - 1],
        fill=C.gold_500
    )
    f_cat = typo.font('kn_var', sf.s(T.meta[0]), weight=700)
    typo.draw_text(
        sf.img, 'ನಿಮ್ಮೂರ ಧ್ವನಿ • CITIZEN JOURNALISM',
        sf.s(m + Grid.rail + 16), sf.s(top + rail_h * 0.72),
        f_cat, C.gold_500
    )
    y = top + rail_h + 30

    # 4. Main Headline (Bold, Urgent, Action-oriented)
    headline = "ನಿಮ್ಮೂರಿನ ಸಮಸ್ಯೆಗೆ ಧ್ವನಿ ಇಲ್ಲವೇ? ನಮಗೆ DM ಮಾಡಿ!"
    hb = typo.fit(
        headline, 'kn',
        sf.s(T.display[0] * 0.82), sf.s(T.h2[0]),
        sf.s(cw), sf.s(220),
        1.22, max_lines=3
    )
    typo.draw_block(sf.img, hb, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += hb.height / sf.ss + 24

    # 5. Standfirst / Sub-headline
    deck_text = (
        "ರಸ್ತೆ, ಕುಡಿಯುವ ನೀರು, ಸೇತುವೆ, ಆಸ್ಪತ್ರೆ, ಶಾಲೆ ಅಥವಾ ಯಾವುದೇ ಸಾರ್ವಜನಿಕ "
        "ಸಮಸ್ಯೆ ಇರಲಿ — ನೇರವಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿಗೆ ತಿಳಿಸಿ. ನಾವು ಸ್ಥಳಕ್ಕೆ ಬಂದು ವರದಿ ಮಾಡಿ, "
        "ಸಂಬಂಧಪಟ್ಟ ಅಧಿಕಾರಿಗಳಿಗೆ ತಲುಪಿಸಿ ಪರಿಹಾರಕ್ಕೆ ಶ್ರಮಿಸುತ್ತೇವೆ."
    )
    f_deck = typo.font('kn_var', sf.s(T.deck[0] * 0.85), weight=440)
    db = typo.layout(deck_text, f_deck, sf.s(cw), 1.42)
    typo.draw_block(sf.img, db, sf.s(m), sf.s(y), C.paper_200, box_w=sf.s(cw))
    y += db.height / sf.ss + 36

    # 6. Action Steps (3 Clear, impactful rows)
    rule(sf, m, y, m + cw, Role.hairline_gold, 1.2)
    y += 28

    steps = [
        ("01", "ಫೋಟೋ ಅಥವಾ ವಿಡಿಯೋ ಕಳುಹಿಸಿ",
         "ಸಮಸ್ಯೆ ಇರುವ ಸ್ಥಳ, ಸ್ಪಷ್ಟ ವಿಡಿಯೋ ಅಥವಾ ಫೋಟೋ ಸಮೇತ ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಕಳುಹಿಸಿ."),
        ("02", "ನಾವು ಸ್ಥಳದಲ್ಲೇ ವರದಿ ಮಾಡುತ್ತೇವೆ",
         "ನಮ್ಮ ವರದಿಗಾರರು ಸ್ಥಳಕ್ಕೆ ಭೇಟಿ ನೀಡಿ, ವಾಸ್ತವ ಸ್ಥಿತಿಯನ್ನು ಸಾರ್ವಜನಿಕರ ಮುಂದಿಡುತ್ತಾರೆ."),
        ("03", "ಅಧಿಕಾರಿಗಳ ಗಮನಕ್ಕೆ • ಪರಿಹಾರಕ್ಕೆ ಪ್ರಯತ್ನ",
         "ಸಮಸ್ಯೆಯನ್ನು ಸಂಬಂಧಪಟ್ಟ ಇಲಾಖೆ ಹಾಗೂ ಶಾಸಕರು/ಅಧಿಕಾರಿಗಳ ಗಮನಕ್ಕೆ ತಂದು ಪರಿಹಾರಕ್ಕೆ ಧ್ವನಿಯಾಗುತ್ತೇವೆ.")
    ]

    for idx, (num, title, desc) in enumerate(steps):
        f_num = typo.font('latin', sf.s(26), weight=750)
        typo.draw_text(sf.img, num, sf.s(m), sf.s(y + 22), f_num, C.gold_500)

        if idx > 0:
            rule(sf, m + 44, y - 6, m + cw, Role.hairline_soft, 1.0)

        f_stitle = typo.font('kn', sf.s(24))
        typo.draw_text(sf.img, title, sf.s(m + 48), sf.s(y + 22), f_stitle, Role.text_hi)

        f_sdesc = typo.font('kn_var', sf.s(20), weight=400)
        typo.draw_text(sf.img, desc, sf.s(m + 48), sf.s(y + 50), f_sdesc, C.paper_300)

        y += 82

    # 7. Big Call-To-Action Banner Box
    y += 15
    cta_h = 100
    panel(sf, [m, y, m + cw, y + cta_h], fill=C.ink_850, outline=alpha(C.gold_500, 0.45), radius=8, weight=1.2)
    
    f_cta_tag = typo.font('kn_var', sf.s(21), weight=600)
    typo.draw_text(
        sf.img, "ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್‌ನಲ್ಲಿ ನೇರವಾಗಿ ಮೆಸೇಜ್ (DM) ಮಾಡಿ:",
        sf.s(m + 24), sf.s(y + 38), f_cta_tag, C.gold_400
    )
    f_handle = typo.font('latin', sf.s(28), weight=750)
    typo.draw_text(
        sf.img, "@OormaniSuddi",
        sf.s(m + 24), sf.s(y + 78), f_handle, Role.text_hi
    )
    
    f_share = typo.font('kn_var', sf.s(20), weight=500)
    typo.draw_text(
        sf.img, "ನಿಮ್ಮೂರಿನ ಜನರೊಂದಿಗೆ ಶೇರ್ ಮಾಡಿ >>",
        sf.s(m + cw - 24), sf.s(y + 58), f_share, C.paper_200, anchor_x='r'
    )

    # 8. Footer
    foot_top = H - 65
    rule(sf, m, foot_top - 20, m + cw, Role.hairline, 1.0)
    cp.footer(sf, m, foot_top, cw, right="ಕರಾವಳಿ • ಉಡುಪಿ • ದಕ್ಷಿಣ ಕನ್ನಡ • ಉತ್ತರ ಕನ್ನಡ")

    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    sf.save(out_path)
    print(f"Saved: {out_path}")


def render_campaign_story_9x16(out_path: str):
    """Render 9:16 (1080x1920) Instagram Story."""
    W, H = 1080, 1920
    sf = Surface(W, H, ss=2)
    m = Grid.margin
    cw = W - 2 * m

    cp.page_base(sf, 0.65)
    radial_glow(sf, W * 0.5, H * 0.40, W * 0.85, C.gold_600, 0.18)
    cp.horizon(sf, H * 0.38, 1.2)

    top = 220
    top = cp.masthead(
        sf, m, top, cw,
        right_top='ವಿಶೇಷ ಅಭಿಯಾನ',
        right_bot='ಕರಾವಳಿ ಜನಧ್ವನಿ'
    ) + 48

    rail_h = 32
    sf.draw.rectangle(
        [sf.s(m), sf.s(top), sf.s(m + Grid.rail) - 1, sf.s(top + rail_h) - 1],
        fill=C.gold_500
    )
    f_cat = typo.font('kn_var', sf.s(T.meta[0]), weight=700)
    typo.draw_text(
        sf.img, 'ನಿಮ್ಮೂರ ಧ್ವನಿ • CITIZEN JOURNALISM',
        sf.s(m + Grid.rail + 16), sf.s(top + rail_h * 0.72),
        f_cat, C.gold_500
    )
    y = top + rail_h + 36

    headline = "ನಿಮ್ಮೂರಿನ ಸಮಸ್ಯೆಗೆ ಧ್ವನಿ ಇಲ್ಲವೇ?\nನಮಗೆ DM ಮಾಡಿ!"
    hb = typo.fit(
        headline, 'kn',
        sf.s(T.display[0] * 0.90), sf.s(T.h1[0]),
        sf.s(cw), sf.s(300),
        1.24, max_lines=3
    )
    typo.draw_block(sf.img, hb, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += hb.height / sf.ss + 30

    deck_text = (
        "ರಸ್ತೆ ಹಾಳಾಗಿದೆಯೇ? ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ ಇದೆಯೇ? ಸೇತುವೆ, ಆಸ್ಪತ್ರೆ ಅಥವಾ ಶಾಲೆಗಳ "
        "ಅವ್ಯವಸ್ಥೆಯಿಂದ ಜನ ಕಷ್ಟಪಡುತ್ತಿದ್ದಾರೆಯೇ? \n\n"
        "ಸುಮ್ಮನಿರಬೇಡಿ — ಸಮಸ್ಯೆಯ ಫೋಟೋ ಅಥವಾ ವಿಡಿಯೋ ನಮಗೆ ಕಳುಹಿಸಿ. ಊರ್ಮನಿ ಸುದ್ದಿ ನಿಮ್ಮೂರಿಗೆ ಬಂದು "
        "ವಾಸ್ತವ ವರದಿ ಮಾಡಿ, ಅಧಿಕಾರಿಗಳ ಗಮನಕ್ಕೆ ತಂದು ಪರಿಹಾರಕ್ಕೆ ಧ್ವನಿಯಾಗುತ್ತದೆ!"
    )
    f_deck = typo.font('kn_var', sf.s(T.deck[0] * 0.88), weight=440)
    db = typo.layout(deck_text, f_deck, sf.s(cw), 1.44)
    typo.draw_block(sf.img, db, sf.s(m), sf.s(y), C.paper_200, box_w=sf.s(cw))
    y += db.height / sf.ss + 48

    rule(sf, m, y, m + cw, Role.hairline_gold, 1.2)
    y += 36

    steps = [
        ("01", "ಫೋಟೋ / ವಿಡಿಯೋ & ಸ್ಥಳ ಕಳುಹಿಸಿ",
         "ಸಮಸ್ಯೆಯ ಸ್ಪಷ್ಟ ವಿಡಿಯೋ ಅಥವಾ ಫೋಟೋ ತೆಗೆದು ಸ್ಥಳದ ವಿವರ ತಿಳಿಸಿ."),
        ("02", "ನಾವು ಸ್ಥಳದಲ್ಲೇ ವರದಿ ಮಾಡುತ್ತೇವೆ",
         "ನಮ್ಮ ವರದಿಗಾರರು ನೇರವಾಗಿ ಬಂದು ಜನರ ಪರವಾಗಿ ವರದಿ ಮಾಡುತ್ತಾರೆ."),
        ("03", "ಅಧಿಕಾರಿಗಳ ಗಮನಕ್ಕೆ • ನೇರ ಪರಿಹಾರ",
         "ಸಂಬಂಧಪಟ್ಟ ಇಲಾಖೆಯ ಮುಂದೆ ಸಮಸ್ಯೆ ಇಟ್ಟು ಪರಿಹಾರಕ್ಕೆ ಶ್ರಮಿಸುತ್ತೇವೆ.")
    ]

    for idx, (num, title, desc) in enumerate(steps):
        f_num = typo.font('latin', sf.s(30), weight=750)
        typo.draw_text(sf.img, num, sf.s(m), sf.s(y + 26), f_num, C.gold_500)

        f_stitle = typo.font('kn', sf.s(26))
        typo.draw_text(sf.img, title, sf.s(m + 54), sf.s(y + 26), f_stitle, Role.text_hi)

        f_sdesc = typo.font('kn_var', sf.s(22), weight=400)
        typo.draw_text(sf.img, desc, sf.s(m + 54), sf.s(y + 60), f_sdesc, C.paper_300)

        if idx > 0:
            rule(sf, m + 50, y - 8, m + cw, Role.hairline_soft, 1.0)

        y += 105

    y += 20
    cta_h = 130
    panel(sf, [m, y, m + cw, y + cta_h], fill=C.ink_850, outline=alpha(C.gold_500, 0.5), radius=10, weight=1.5)

    f_cta_tag = typo.font('kn_var', sf.s(24), weight=600)
    typo.draw_text(
        sf.img, "ಮೆಸೇಜ್ ಕಳುಹಿಸಲು ನೇರವಾಗಿ DM ಮಾಡಿ:",
        sf.s(m + 28), sf.s(y + 44), f_cta_tag, C.gold_400
    )
    f_handle = typo.font('latin', sf.s(34), weight=750)
    typo.draw_text(
        sf.img, "@OormaniSuddi",
        sf.s(m + 28), sf.s(y + 92), f_handle, Role.text_hi
    )

    foot_top = H - 180
    rule(sf, m, foot_top - 20, m + cw, Role.hairline, 1.0)
    cp.footer(sf, m, foot_top, cw, right="ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ")

    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    sf.save(out_path)
    print(f"Saved: {out_path}")


def render_campaign_square_1x1(out_path: str):
    """Render 1:1 (1080x1080) Square Post."""
    W, H = 1080, 1080
    sf = Surface(W, H, ss=2)
    m = Grid.margin
    cw = W - 2 * m

    cp.page_base(sf, 0.6)
    radial_glow(sf, W * 0.5, H * 0.45, W * 0.75, C.gold_600, 0.15)
    cp.horizon(sf, H * 0.42, 0.9)

    top = cp.masthead(
        sf, m, 48, cw,
        right_top='ವಿಶೇಷ ಅಭಿಯಾನ',
        right_bot='ಕರಾವಳಿ ಜನಧ್ವನಿ'
    ) + 32

    rail_h = 28
    sf.draw.rectangle(
        [sf.s(m), sf.s(top), sf.s(m + Grid.rail) - 1, sf.s(top + rail_h) - 1],
        fill=C.gold_500
    )
    f_cat = typo.font('kn_var', sf.s(T.meta[0] * 0.92), weight=700)
    typo.draw_text(
        sf.img, 'ನಿಮ್ಮೂರ ಧ್ವನಿ • CITIZEN JOURNALISM',
        sf.s(m + Grid.rail + 14), sf.s(top + rail_h * 0.72),
        f_cat, C.gold_500
    )
    y = top + rail_h + 24

    headline = "ನಿಮ್ಮೂರಿನ ಸಮಸ್ಯೆಗೆ ಧ್ವನಿ ಇಲ್ಲವೇ? ನಮಗೆ DM ಮಾಡಿ!"
    hb = typo.fit(
        headline, 'kn',
        sf.s(T.h1[0] * 0.95), sf.s(T.h3[0]),
        sf.s(cw), sf.s(180),
        1.22, max_lines=2
    )
    typo.draw_block(sf.img, hb, sf.s(m), sf.s(y), Role.text_hi, box_w=sf.s(cw))
    y += hb.height / sf.ss + 20

    deck_text = (
        "ರಸ್ತೆ, ನೀರು, ಸೇತುವೆ, ಆಸ್ಪತ್ರೆ ಅಥವಾ ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಸಮಸ್ಯೆ ಇರಲಿ — ನಮಗೆ ಫೋಟೋ/ವಿಡಿಯೋ "
        "ಸಮೇತ DM ಮಾಡಿ. ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳಕ್ಕೆ ಬಂದು ವರದಿ ಮಾಡಿ, ಅಧಿಕಾರಿಗಳ ಗಮನಕ್ಕೆ ತಂದು ಪರಿಹಾರಕ್ಕೆ ಶ್ರಮಿಸುತ್ತದೆ."
    )
    f_deck = typo.font('kn_var', sf.s(22), weight=440)
    db = typo.layout(deck_text, f_deck, sf.s(cw), 1.40)
    typo.draw_block(sf.img, db, sf.s(m), sf.s(y), C.paper_200, box_w=sf.s(cw))
    y += db.height / sf.ss + 28

    cta_h = 92
    panel(sf, [m, y, m + cw, y + cta_h], fill=C.ink_850, outline=alpha(C.gold_500, 0.45), radius=8, weight=1.2)
    
    f_cta_tag = typo.font('kn_var', sf.s(20), weight=600)
    typo.draw_text(
        sf.img, "ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್‌ನಲ್ಲಿ ನೇರವಾಗಿ ಮೆಸೇಜ್ ಮಾಡಿ:",
        sf.s(m + 22), sf.s(y + 34), f_cta_tag, C.gold_400
    )
    f_handle = typo.font('latin', sf.s(28), weight=750)
    typo.draw_text(
        sf.img, "@OormaniSuddi",
        sf.s(m + 22), sf.s(y + 74), f_handle, Role.text_hi
    )

    f_share = typo.font('kn_var', sf.s(19), weight=500)
    typo.draw_text(
        sf.img, "ಶೇರ್ ಮಾಡಿ ಜಾಗೃತಿ ಮೂಡಿಸಿ >>",
        sf.s(m + cw - 22), sf.s(y + 54), f_share, C.paper_200, anchor_x='r'
    )

    foot_top = H - 56
    rule(sf, m, foot_top - 18, m + cw, Role.hairline, 1.0)
    cp.footer(sf, m, foot_top, cw, right="ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ")

    grain(sf, Grade.grain, Grade.grain_shadow_bias)
    sf.save(out_path)
    print(f"Saved: {out_path}")


def main():
    p1 = os.path.join(OUT_DIR, "announcement_post_4x5.jpg")
    p2 = os.path.join(OUT_DIR, "announcement_story_9x16.jpg")
    p3 = os.path.join(OUT_DIR, "announcement_square_1x1.jpg")
    render_campaign_post_4x5(p1)
    render_campaign_story_9x16(p2)
    render_campaign_square_1x1(p3)
    print("All campaign artwork rendered successfully!")


if __name__ == '__main__':
    main()
