"""Stylised anatomy drawn as SVG (viewBox 0 0 1000 1000). No patient images, ever.

Each organ uses four tissue classes whose colours depend on the modality look
(set by CSS in the template):
  .soft   – soft tissue           .bright – echogenic tissue / bone / fat
  .fluid  – fluid (bile, urine)   .air    – air (lungs, bowel gas)
Anchors are points annotations can point to.
"""

ORGANS = {}


def organ(name, default, anchors, *, describe):
    def deco(fn):
        ORGANS[name] = {"svg": fn(), "default": default, "anchors": anchors, "describe": describe}
        return fn
    return deco


@organ("liver", "us", {"center": (500, 450), "upper": (560, 330), "lower": (420, 590), "edge": (790, 420)},
       describe="liver (with fatty-liver brightness possible)")
def _liver():
    return """
<path class="soft" d="M170 400 C 230 250 520 215 770 300 C 875 335 890 430 825 480 C 700 575 420 660 255 615 C 160 585 130 480 170 400 Z"/>
<path class="bright" opacity=".25" d="M300 330 C 420 300 560 300 680 340" fill="none" stroke-width="10"/>
<g class="fluid" opacity=".85"><ellipse cx="420" cy="430" rx="22" ry="12"/><ellipse cx="560" cy="470" rx="18" ry="10"/><ellipse cx="640" cy="390" rx="14" ry="8"/></g>
<path class="bright" d="M690 515 C 760 520 790 600 750 650 C 715 690 650 680 640 630 C 630 580 640 520 690 515Z" opacity=".001"/>"""


@organ("gallbladder", "us", {"center": (560, 520), "stone": (600, 590), "wall": (470, 470)},
       describe="gallbladder, can show a stone with acoustic shadow")
def _gb():
    return """
<path class="soft" d="M120 300 C 300 200 700 200 880 320 L 880 820 L 120 820 Z" opacity=".9"/>
<path class="fluid" d="M420 380 C 560 330 720 420 700 560 C 680 690 560 720 480 660 C 400 600 330 420 420 380 Z"/>
<path class="bright" fill="none" stroke-width="10" d="M420 380 C 560 330 720 420 700 560 C 680 690 560 720 480 660 C 400 600 330 420 420 380 Z"/>
<circle class="bright" cx="600" cy="600" r="34"/>
<path class="air" opacity=".85" d="M566 630 L 634 630 L 680 900 L 520 900 Z"/>"""


@organ("kidney", "us", {"center": (480, 540), "upper": (470, 330), "lower": (480, 770), "sinus": (490, 540)},
       describe="kidney with central sinus; can show stone or swelling (hydronephrosis)")
def _kidney():
    return """
<path class="soft" d="M430 230 C 580 205 665 330 640 455 C 628 515 575 525 575 565 C 575 605 628 625 640 690 C 660 815 555 875 440 835 C 320 795 295 650 305 525 C 318 375 330 250 430 230Z"/>
<path class="bright" d="M470 360 C 540 380 560 470 540 540 C 520 610 540 690 500 730 C 450 690 430 610 440 540 C 448 470 420 400 470 360Z"/>
<path class="soft" fill="none" stroke-width="6" opacity=".6" d="M370 300 C 330 420 330 650 380 780"/>"""


@organ("thyroid", "us", {"left": (330, 500), "right": (670, 500), "center": (500, 520), "nodule": (690, 470)},
       describe="thyroid gland (two lobes) with trachea; can show a nodule")
def _thyroid():
    return """
<path class="soft" d="M120 260 L 880 260 L 880 340 L 120 340 Z" opacity=".55"/>
<path class="soft" d="M500 470 C 430 420 360 360 280 380 C 190 405 180 560 250 620 C 320 680 430 610 500 580 C 570 610 680 680 750 620 C 820 560 810 405 720 380 C 640 360 570 420 500 470Z"/>
<circle class="air" cx="500" cy="620" r="95"/>
<circle class="bright" cx="500" cy="620" r="95" fill="none" stroke-width="14"/>
<ellipse class="fluid" cx="690" cy="470" rx="48" ry="38" opacity=".9"/>
<ellipse class="fluid" cx="170" cy="560" rx="40" ry="60"/><ellipse class="fluid" cx="830" cy="560" rx="40" ry="60"/>"""


@organ("heart", "us", {"center": (500, 500), "left": (600, 560), "right": (400, 560), "upper": (500, 330)},
       describe="heart with four chambers")
def _heart():
    return """
<path class="soft" d="M500 230 C 640 200 790 300 790 470 C 790 650 650 790 500 830 C 350 790 210 650 210 470 C 210 300 360 200 500 230Z"/>
<ellipse class="fluid" cx="410" cy="420" rx="85" ry="95"/><ellipse class="fluid" cx="590" cy="420" rx="85" ry="95"/>
<ellipse class="fluid" cx="420" cy="620" rx="95" ry="120"/><ellipse class="fluid" cx="580" cy="620" rx="95" ry="120"/>
<path class="bright" d="M500 330 L 500 760" stroke-width="16" fill="none"/>"""


@organ("uterus", "us", {"center": (500, 520), "lining": (500, 500), "left": (230, 560), "right": (770, 560)},
       describe="uterus with lining and both ovaries (follicles possible)")
def _uterus():
    return """
<path class="soft" d="M500 300 C 640 300 700 400 680 520 C 660 640 580 700 520 760 L 480 760 C 420 700 340 640 320 520 C 300 400 360 300 500 300Z"/>
<path class="bright" d="M500 360 C 560 400 560 560 510 680 C 470 560 440 400 500 360Z"/>
<ellipse class="soft" cx="210" cy="560" rx="90" ry="65"/><ellipse class="soft" cx="790" cy="560" rx="90" ry="65"/>
<g class="fluid"><circle cx="185" cy="545" r="16"/><circle cx="230" cy="580" r="13"/><circle cx="215" cy="530" r="10"/>
<circle cx="770" cy="545" r="15"/><circle cx="810" cy="585" r="12"/><circle cx="800" cy="530" r="10"/></g>"""


@organ("pregnancy", "us", {"center": (500, 520), "head": (380, 470), "fluid": (650, 640), "placenta": (500, 260)},
       describe="pregnancy: baby in amniotic fluid with placenta (never anything about sex of the baby)")
def _preg():
    return """
<path class="soft" d="M500 210 C 720 210 860 360 860 540 C 860 720 700 840 500 840 C 300 840 140 720 140 540 C 140 360 280 210 500 210Z"/>
<path class="fluid" d="M500 300 C 680 300 780 410 780 550 C 780 690 660 770 500 770 C 340 770 220 690 220 550 C 220 410 320 300 500 300Z"/>
<path class="bright" d="M300 260 C 420 215 580 215 700 260 L 690 300 C 580 270 420 270 310 300 Z" opacity=".9"/>
<circle class="bright" cx="380" cy="470" r="88" fill="none" stroke-width="14"/>
<circle class="soft" cx="380" cy="470" r="80" opacity=".7"/>
<path class="soft" d="M455 500 C 540 470 640 500 660 570 C 680 640 610 690 540 680 C 480 670 440 600 455 500Z" opacity=".85"/>"""


@organ("bladder", "us", {"center": (500, 470), "prostate": (500, 700), "wall": (330, 470)},
       describe="urinary bladder (full) with prostate below")
def _bladder():
    return """
<path class="soft" d="M120 260 L 880 260 L 880 840 L 120 840 Z" opacity=".85"/>
<path class="fluid" d="M330 330 C 420 300 580 300 670 330 C 720 400 720 540 670 600 C 580 630 420 630 330 600 C 280 540 280 400 330 330Z"/>
<path class="bright" fill="none" stroke-width="8" d="M330 330 C 420 300 580 300 670 330 C 720 400 720 540 670 600 C 580 630 420 630 330 600 C 280 540 280 400 330 330Z"/>
<ellipse class="soft" cx="500" cy="710" rx="120" ry="80" opacity=".95"/><ellipse class="bright" cx="500" cy="705" rx="40" ry="26" opacity=".5"/>"""


@organ("breast", "us", {"center": (520, 560), "lesion": (520, 560), "skin": (500, 300)},
       describe="breast tissue layers with an oval lump")
def _breast():
    return """
<path class="bright" d="M120 280 L 880 280 L 880 310 L 120 310Z"/>
<path class="soft" d="M120 310 L 880 310 L 880 420 L 120 420Z" opacity=".8"/>
<path class="bright" d="M120 420 C 300 400 700 440 880 410 L 880 720 C 700 740 300 700 120 730Z" opacity=".75"/>
<ellipse class="fluid" cx="520" cy="560" rx="110" ry="62" opacity=".92"/>
<path class="soft" d="M120 730 C 300 700 700 740 880 720 L 880 860 L 120 860Z"/>"""


@organ("vessel", "doppler", {"split": (500, 500), "plaque": (610, 420), "lower": (500, 760), "upper": (360, 300)},
       describe="artery splitting in two (like the carotid) with colour Doppler flow; can show plaque")
def _vessel():
    return """
<path class="soft" d="M120 220 L 880 220 L 880 860 L 120 860Z" opacity=".75"/>
<path class="lumen" d="M440 860 L 440 540 C 440 470 380 400 300 220 L 400 220 C 470 380 500 440 520 470 C 545 430 600 340 650 220 L 750 220 C 690 380 580 470 560 540 L 560 860 Z"/>
<path class="flow" d="M460 860 L 460 545 C 460 480 400 410 330 220 L 375 220 C 445 380 490 450 512 500 C 535 445 585 360 625 220 L 690 220 C 640 360 560 460 540 545 L 540 860 Z"/>
<path class="bright" d="M600 400 C 640 360 665 330 680 300 L 700 310 C 680 360 650 400 615 430Z"/>"""


@organ("brain", "ct", {"center": (500, 500), "ventricles": (500, 470), "left": (330, 520), "right": (670, 520)},
       describe="brain in a skull (CT/MRI cross-section) with ventricles")
def _brain():
    return """
<ellipse class="bright" cx="500" cy="500" rx="330" ry="390"/>
<ellipse class="soft" cx="500" cy="500" rx="300" ry="360"/>
<path class="fluid" d="M500 380 C 440 380 420 420 440 470 C 455 510 470 540 500 560 C 530 540 545 510 560 470 C 580 420 560 380 500 380Z"/>
<path class="fluid" d="M470 600 C 480 640 520 640 530 600 Z"/>
<path class="bright" fill="none" stroke-width="4" opacity=".35" d="M500 150 L 500 850"/>
<g class="bright" fill="none" stroke-width="5" opacity=".18"><path d="M260 380 C 300 340 330 400 300 440"/><path d="M740 380 C 700 340 670 400 700 440"/><path d="M270 620 C 320 600 330 660 290 690"/><path d="M730 620 C 680 600 670 660 710 690"/></g>"""


@organ("chest", "xray", {"center": (500, 520), "left": (670, 500), "right": (330, 500), "heart": (540, 620)},
       describe="chest X-ray: ribs, lungs and heart shadow")
def _chest():
    ribs = "".join(f'<path d="M500 {250+i*70} C 400 {230+i*70} 250 {260+i*72} 190 {330+i*75}"/>'
                   f'<path d="M500 {250+i*70} C 600 {230+i*70} 750 {260+i*72} 810 {330+i*75}"/>' for i in range(7))
    return f"""
<path class="soft" d="M140 180 L 860 180 L 900 900 L 100 900Z"/>
<path class="air" d="M470 260 C 360 250 230 330 210 520 C 200 650 230 760 300 800 C 380 790 450 760 470 700Z"/>
<path class="air" d="M530 260 C 640 250 770 330 790 520 C 800 650 770 760 700 800 C 620 790 550 760 530 700Z"/>
<path class="soft" d="M470 470 C 430 560 420 690 520 760 C 640 790 700 700 680 610 C 660 540 590 500 530 470Z"/>
<g class="bright" fill="none" stroke-width="16" opacity=".55">{ribs}</g>
<path class="bright" d="M480 180 L 520 180 L 520 900 L 480 900Z" opacity=".5"/>"""


@organ("spine", "mri", {"center": (500, 520), "disc": (500, 560), "cord": (610, 500), "upper": (480, 260)},
       describe="spine side view: vertebrae, discs and spinal cord")
def _spine():
    v = "".join(f'<rect class="soft" x="360" y="{160+i*150}" width="230" height="110" rx="22"/>'
                f'<rect class="fluid" x="368" y="{272+i*150}" width="214" height="36" rx="16"/>' for i in range(5))
    return f"""
<path class="soft" d="M120 120 L 880 120 L 880 900 L 120 900Z" opacity=".4"/>
{v}
<rect class="fluid" x="610" y="140" width="70" height="760" rx="30"/>
<rect class="soft" x="628" y="140" width="34" height="760" rx="17"/>
<path class="fluid" d="M590 560 C 620 550 640 560 640 580 C 620 600 600 600 582 590 Z" opacity=".001"/>"""


@organ("knee", "mri", {"center": (500, 520), "joint": (500, 520), "upper": (500, 300), "lower": (500, 760)},
       describe="knee joint: thigh bone, shin bone and the joint space")
def _knee():
    return """
<path class="soft" d="M260 120 L 740 120 L 760 900 L 240 900Z" opacity=".6"/>
<path class="bright" d="M380 120 L 620 120 L 640 400 C 660 460 600 490 500 480 C 400 490 340 460 360 400Z"/>
<path class="bright" d="M340 560 C 420 545 580 545 660 560 L 630 900 L 370 900Z"/>
<path class="fluid" d="M350 480 C 430 500 570 500 650 480 L 660 560 C 580 545 420 545 340 560Z" opacity=".75"/>"""


@organ("abdomen_ct", "ct", {"center": (500, 520), "liver": (330, 480), "spine": (500, 720), "kidney": (650, 620)},
       describe="CT cross-section of the belly: liver, spine, kidneys, bowel")
def _abd():
    return """
<ellipse class="soft" cx="500" cy="520" rx="400" ry="320"/>
<ellipse class="bright" cx="500" cy="520" rx="400" ry="320" fill="none" stroke-width="18" opacity=".6"/>
<path class="soft" d="M150 470 C 200 330 360 300 440 360 C 470 450 420 560 300 600 C 210 610 150 560 150 470Z" style="filter:brightness(1.15)"/>
<circle class="bright" cx="500" cy="720" r="58"/><circle class="fluid" cx="500" cy="720" r="24"/>
<ellipse class="soft" cx="650" cy="640" rx="55" ry="80" style="filter:brightness(1.2)"/><ellipse class="soft" cx="350" cy="660" rx="55" ry="80" style="filter:brightness(1.2)"/>
<g class="air"><ellipse cx="600" cy="420" rx="45" ry="30"/><ellipse cx="700" cy="480" rx="35" ry="25"/><ellipse cx="540" cy="520" rx="30" ry="22"/></g>
<circle class="bright" cx="520" cy="620" r="22" opacity=".8"/>"""


@organ("body", "diagram", {"head": (500, 150), "chest": (500, 330), "abdomen": (500, 470), "pelvis": (500, 580), "knee": (430, 800)},
       describe="whole-body outline for general topics (which scan, radiation, etc.)")
def _body():
    return """
<g class="line" fill="none" stroke-width="10" stroke-linejoin="round" stroke-linecap="round">
<circle cx="500" cy="140" r="70"/>
<path d="M440 215 C 360 230 330 260 320 330 L 290 560 M560 215 C 640 230 670 260 680 330 L 710 560"/>
<path d="M400 240 C 390 380 395 520 410 620 L 420 900 M600 240 C 610 380 605 520 590 620 L 580 900"/>
<path d="M410 620 C 450 640 550 640 590 620 M500 640 L 490 900"/>
</g>"""


@organ("ct_scanner", "diagram", {"ring": (500, 420), "table": (650, 640), "center": (500, 420)},
       describe="CT scanner: ring-shaped machine with a moving table")
def _ct():
    return """
<g class="line" fill="none" stroke-width="10"><circle cx="500" cy="420" r="300"/><circle cx="500" cy="420" r="150"/></g>
<path class="line-fill" d="M120 610 L 880 610 L 880 650 L 120 650Z"/><path class="line-fill" d="M480 650 L 520 650 L 540 860 L 460 860Z"/>
<g class="accent" fill="none" stroke-width="6" stroke-dasharray="14 12"><path d="M500 120 L 500 270"/><path d="M290 210 L 395 315"/><path d="M710 210 L 605 315"/></g>"""


@organ("mri_machine", "diagram", {"tube": (500, 440), "table": (500, 690), "center": (500, 440)},
       describe="MRI machine: a long tube with a strong magnet and a table")
def _mri():
    return """
<g class="line" fill="none" stroke-width="10"><rect x="160" y="180" width="680" height="520" rx="80"/><ellipse cx="500" cy="440" rx="190" ry="170"/></g>
<path class="line-fill" d="M90 660 L 910 660 L 910 700 L 90 700Z"/>
<g class="accent" fill="none" stroke-width="7"><path d="M250 260 C 230 300 230 340 250 380"/><path d="M215 240 C 185 300 185 360 215 420"/><path d="M750 260 C 770 300 770 340 750 380"/><path d="M785 240 C 815 300 815 360 785 420"/></g>"""


@organ("us_probe", "diagram", {"probe": (500, 260), "beam": (500, 600), "center": (500, 520)},
       describe="ultrasound probe sending sound waves into the body")
def _probe():
    arcs = "".join(f'<path d="M{500-60-i*55} {470+i*80} Q 500 {520+i*95} {500+60+i*55} {470+i*80}"/>' for i in range(4))
    return f"""
<path class="line-fill" d="M430 120 L 570 120 L 590 340 C 590 380 410 380 410 340 Z"/>
<path class="line" fill="none" stroke-width="10" d="M120 420 C 300 400 700 400 880 420"/>
<g class="accent" fill="none" stroke-width="7">{arcs}</g>"""


ORGAN_NAMES = list(ORGANS)
MODALITIES = {
    "us": "Ultrasound", "doppler": "Doppler ultrasound", "ct": "CT", "mri": "MRI", "xray": "X-ray", "diagram": "Diagram",
}


def catalogue_text():
    """For the writer prompt: what visuals exist."""
    lines = [f"- {n}: {o['describe']} (looks best as {o['default']}; anchors: {', '.join(o['anchors'])})"
             for n, o in ORGANS.items()]
    return "\n".join(lines)
