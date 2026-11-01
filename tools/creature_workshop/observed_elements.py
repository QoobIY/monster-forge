"""Observed modular mage and elemental sheets; every primitive has an explicit slot."""
from __future__ import annotations

from tools.creature_workshop.authoring import STAGES, Builder


class PartBuilder(Builder):
    """Author directly inside a part; never infer anatomy from a mesh filename."""

    def __init__(self, identity: str, palette: dict):
        super().__init__()
        self.identity = identity
        self.palette = palette
        self.slot = "torso"

    def add(self, op, part, material, purpose, **parameters):
        super().add(op, part, material, purpose, **parameters)
        self.commands[-1]["slot"] = self.slot

    def recipe(self) -> dict:
        return {"schema_version": 1, "id": self.identity, "label": self.identity,
                "coordinate_system": "metres; Y up; +Z forward; floor Y=0",
                "palette": self.palette, "stages": STAGES, "commands": self.commands}


def _mage_masses(b: PartBuilder, width: float, *, boots: bool = True):
    b.loft("chest", "primary", [[1.04, 0, 0, .23*width, .17],
                                [1.48, 0, 0, .33*width, .24],
                                [1.74, 0, -.02, .27*width, .19]],
           "Трапециевидный торс одежды: талия уже грудной клетки")
    b.tube("neck", "skin", [[0, 1.73, 0], [0, 1.94, .01]], [.12, .115],
           "Шейный соединительный объём в общей системе координат", 8)
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_leg"
        b.tube("leg", "primary", [[sign*.19*width, 1.02, 0],
                                 [sign*.20*width, .56, .015], [sign*.21*width, .18, .03]],
               [.16, .11, .09], "Самостоятельная нога от среза бедра до щиколотки", 6)
        if boots:
            b.loft("boot", "dark", [[0, sign*.21*width, .12, .145, .23],
                                    [.12, sign*.21*width, .12, .145, .23],
                                    [.23, sign*.21*width, .035, .095, .11]],
                   "Широкий угловатый сапог; нижний срез точно Y=0", 6)
        b.slot = side+"_arm"
        b.tube("sleeve_core", "primary", [[sign*.34*width, 1.62, 0],
                                         [sign*.51*width, 1.27, .01],
                                         [sign*.63*width, .95, .08]], [.16, .13, .12],
               "Самостоятельная опущенная рука: плечо, локоть, запястье", 6)
        b.oval("palm", "skin", [sign*.65*width, .86, .12], [.09, .12, .09],
               "Ладонь пустой кисти, оружие отсутствует", 6)
    b.slot = "torso"


def _face(b: PartBuilder, *, hood: bool, hair: bool, elf: bool, beard: bool):
    b.slot = "head"
    b.stage = 2
    y = 2.12
    b.oval("face", "skin", [0, y, .04], [.205, .265, .185],
           "Гранёное лицо с широкими скуловыми плоскостями", 8)
    b.loft("jaw", "skin", [[y-.26, 0, .05, .08, .10],
                           [y-.15, 0, .085, .16, .14],
                           [y-.04, 0, .07, .18, .15]], "Сужение челюсти к подбородку", 6)
    for sign in (-1, 1):
        b.plate("eye", "dark", [[sign*.105-.038, y+.049, .222],
                                 [sign*.105+.038, y+.049, .222],
                                 [sign*.105+.031, y+.015, .223],
                                 [sign*.105-.030, y+.015, .223]],
                "Тёмный глаз под широкой надбровной гранью", .016)
        b.tube("brow", "skin", [[sign*.058, y+.085, .215],
                                [sign*.161, y+.060, .19]], [.035, .023],
               "Угловатая крупная надбровная дуга", 4)
        if elf:
            b.plate("ear", "skin", [[sign*.16, y+.09, -.005],
                                    [sign*.39, y+.20, -.025],
                                    [sign*.23, y-.04, .025]],
                    "Большое острое эльфийское ухо, выступающее из капюшона", .045)
    b.plate("nose", "skin", [[-.045, y+.07, .211], [.045, y+.07, .211],
                              [.07, y-.095, .245], [0, y-.075, .30],
                              [-.07, y-.095, .245]], "Крупный многогранный выступ носа", .03)
    b.box("mouth", "dark", [0, y-.135, .239], [.102, .017, .018],
          "Короткая линия сомкнутого рта")
    if hood:
        b.loft("hood_back", "primary", [[y-.27, 0, -.055, .25, .20],
                                        [y+.10, 0, -.06, .28, .22],
                                        [y+.41, 0, -.01, .025, .025]],
               "Заострённая тыльная оболочка капюшона", 6)
        for sign in (-1, 1):
            b.tube("hood_edge", "accent", [[0, y+.35, .14],
                                           [sign*.23, y+.07, .13],
                                           [sign*.22, y-.26, .06]],
                   [.025, .035, .025], "Широкая светлая окантовка открытого капюшона", 4)
    if hair:
        b.oval("hair_back", "hair", [0, y+.07, -.08], [.26, .30, .20],
               "Светлая затылочная масса волос", 8)
        for sign in (-1, 1):
            b.tube("hair_lock", "hair", [[sign*.13, y+.28, .04],
                                         [sign*.215, y+.04, .035],
                                         [sign*.23, y-.28, .07],
                                         [sign*.19, y-.41, .105]],
                   [.095, .07, .055, .012], "Длинная светлая гранёная прядь вдоль лица", 5)
    if beard:
        b.loft("beard", "accent", [[y-.56, 0, .23, .008, .008],
                                    [y-.21, 0, .24, .15, .11],
                                    [y-.10, 0, .19, .14, .08]],
               "Очень длинная светлая борода с острым нижним концом", 5)
        for sign in (-1, 1):
            b.tube("moustache", "accent", [[0, y-.08, .25],
                                           [sign*.13, y-.14, .24]], [.035, .025],
                   "Две широкие светлые половины усов", 4)


def _robe(b: PartBuilder, width: float, *, pointed: bool):
    b.stage = 3
    b.slot = "torso"
    b.loft("skirt", "primary", [[.47, 0, -.01, .40*width, .24],
                                [.77, 0, -.01, .31*width, .22],
                                [1.09, 0, -.01, .23*width, .19]],
           "Длинный расширяющийся подол торса; ноги сохраняются самостоятельными", 8)
    b.loft("belt", "dark", [[1.04, 0, 0, .25*width, .22],
                             [1.16, 0, 0, .25*width, .22]], "Широкий гладкий пояс без мелкого орнамента")
    for sign in (-1, 1):
        b.plate("lapel", "accent", [[sign*.27*width, 1.74, .20],
                                    [sign*.32*width, 1.71, .22],
                                    [sign*.035, 1.34, .263], [0, 1.38, .27]],
                "Светлая V-образная лопасть грудной окантовки", .025)
        b.plate("skirt_trim", "accent", [[sign*.035, 1.03, .235],
                                         [sign*.080, 1.03, .235],
                                         [sign*.27*width, .49, .245],
                                         [sign*.20*width, .47, .249]],
                "Широкая светлая полоса на своей стороне подола", .02)
        b.slot = ("left" if sign < 0 else "right")+"_arm"
        b.loft("cuff", "primary", [[.85, sign*.65*width, .075, .20, .17],
                                   [1.06, sign*.59*width, .06, .145, .13],
                                   [1.31, sign*.49*width, .02, .125, .125]],
               "Широкий раскрытый рукав с крупным нижним краем", 6)
        b.plate("cuff_trim", "accent", [[sign*.65*width-.19, .89, .23],
                                        [sign*.65*width, 1.04, .23],
                                        [sign*.65*width+.19, .89, .23],
                                        [sign*.65*width+.19, .84, .23],
                                        [sign*.65*width, .98, .23],
                                        [sign*.65*width-.19, .84, .23]],
                "Широкая светлая угловая кайма края рукава", .025)
    b.slot = "torso"
    if pointed:
        b.plate("front_tabard", "primary", [[-.14, 1.04, .259], [.14, 1.04, .259],
                                            [.13, .43, .26], [0, .31, .27],
                                            [-.13, .43, .26]], "Острый центральный конец мантии", .035)


def _hands(b: PartBuilder, width: float):
    b.stage = 5
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_arm"
        for i in range(3):
            x = sign*.65*width+(i-1)*.044
            b.tube("finger", "skin", [[x, .81, .16], [x, .67, .20], [x, .63, .17]],
                   [.023, .021, .012], "Крупный отдельный согнутый палец пустой кисти", 4)
        b.tube("thumb", "skin", [[sign*(.65*width-.07), .87, .15],
                                  [sign*(.65*width-.12), .77, .19]],
               [.035, .022], "Отведённый внутрь большой палец", 4)


def _leg_panels(b: PartBuilder, width: float, *, ankle: bool):
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_leg"
        x = sign*.21*width
        b.plate("leg_cloth", "primary", [[x-.12, 1.02, .09], [x+.12, 1.02, .09],
                                         [x+.14, .30, .12], [x+.03, .21, .16],
                                         [x-.14, .30, .12]],
                "Длинная самостоятельная тканевая лопасть своей ноги", .06)
        b.plate("leg_trim", "accent", [[x-.025, 1.00, .163], [x+.025, 1.00, .163],
                                        [x+.08, .29, .19], [x+.025, .25, .195]],
                "Широкая золотистая полоса ткани ноги", .024)
        if ankle:
            b.loft("ankle_band", "accent", [[.17, x, .025, .112, .13],
                                             [.25, x, .025, .112, .13]],
                   "Широкий золотистый край над тёмным сапогом", 6)
    b.slot = "torso"


def supreme_summoner() -> dict:
    b = PartBuilder("supreme-summoner", {"primary": "873e51", "accent": "dcb779",
                                        "skin": "d4ae92", "dark": "673d34", "hair": "e6dfce"})
    _mage_masses(b, .85)
    _face(b, hood=False, hair=True, elf=False, beard=False)
    _robe(b, .85, pointed=True)
    _leg_panels(b, .85, ankle=False)
    b.stage = 4
    for sign in (-1, 1):
        b.plate("high_collar", "primary", [[sign*.08, 1.51, .11],
                                          [sign*.33, 1.82, -.015],
                                          [sign*.29, 2.02, -.045],
                                          [sign*.10, 1.92, -.045]],
                "Высокая расходящаяся лопасть воротника позади шеи", .08)
        b.tube("collar_trim", "accent", [[sign*.075, 1.55, .15],
                                         [sign*.24, 1.86, .015],
                                         [sign*.29, 2.02, -.005]], [.025, .03, .022],
               "Крупная золотистая внутренняя полоса воротника", 4)
    _hands(b, .85)
    return b.recipe()


def grand_wizard() -> dict:
    b = PartBuilder("grand-wizard", {"primary": "3d414b", "accent": "aeaa90",
                                    "skin": "c6aa91", "dark": "75776f"})
    _mage_masses(b, .92)
    _face(b, hood=True, hair=False, elf=False, beard=True)
    _robe(b, .92, pointed=False)
    b.stage = 4
    b.slot = "torso"
    b.plate("split_tabard", "accent", [[-.09, 1.03, .25], [.09, 1.03, .25],
                                       [.16, .43, .25], [.02, .55, .26],
                                       [0, .57, .26], [-.16, .43, .25]],
            "Светлая центральная лопасть с раздвоенным нижним краем", .03)
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_leg"
        b.loft("ankle_edge", "accent", [[.17, sign*.21*.92, .025, .112, .13],
                                        [.25, sign*.21*.92, .025, .112, .13]],
               "Светлый широкий край сапога, видимый на листе", 6)
    _hands(b, .92)
    return b.recipe()


def mighty_warlock() -> dict:
    b = PartBuilder("mighty-warlock", {"primary": "a13f39", "accent": "d4ab59",
                                      "skin": "d1b997", "dark": "382e39"})
    _mage_masses(b, .91)
    _face(b, hood=True, hair=False, elf=True, beard=False)
    _robe(b, .91, pointed=True)
    _leg_panels(b, .91, ankle=True)
    b.slot = "torso"
    b.stage = 4
    b.plate("inner_robe", "dark", [[-.10, 1.71, .26], [.10, 1.71, .26],
                                    [.07, 1.15, .272], [0, 1.05, .28],
                                    [-.07, 1.15, .272]], "Тёмная внутренняя V-панель грудной одежды")
    b.plate("belt_gem", "accent", [[0, 1.28, .29], [.105, 1.13, .30],
                                    [0, .96, .31], [-.105, 1.13, .30]],
            "Большой ромбический золотой камень пояса", .075)
    for sign, side in ((-1, "left"), (1, "right")):
        for index in range(3):
            x = sign*(.24+.08*index)
            h = .38 if index == 1 else .23
            b.tube("shoulder_crystal", "accent", [[x, 1.70, -.02],
                                                   [x+sign*.02, 1.79, -.035],
                                                   [x+sign*.06, 1.79+h, -.02]],
                   [.085, .08, .003], "Один из трёх крупных золотых кристаллов плеча торса", 4)
        b.slot = side+"_arm"
        for index in range(2):
            x = sign*(.35+.085*index)
            b.tube("arm_crystal", "accent", [[x, 1.57, .005],
                                             [x+sign*.05, 1.77+.10*index, .01]],
                   [.078, .003], "Один из двух золотых кристаллов отдельной руки", 4)
        b.slot = "torso"
    _hands(b, .91)
    return b.recipe()


def water_elemental() -> dict:
    b = PartBuilder("water-elemental", {"primary": "378ca4", "accent": "a0e5dd",
                                       "skin": "62b2bf", "dark": "254d6a"})
    b.loft("water_body", "primary", [[.22, 0, -.07, .014, .014],
                                     [.55, .03, -.03, .12, .11], [.91, 0, 0, .23, .20],
                                     [1.34, 0, 0, .38, .25], [1.68, 0, -.02, .41, .26],
                                     [1.87, 0, 0, .09, .09]],
           "Единый водный корпус: широкая грудь и длинный парящий острый хвост", 8)
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_wisp"
        b.tube("water_arm", "primary", [[sign*.39, 1.65, 0],
                                         [sign*.61, 1.31, .01], [sign*.70, .91, .09]],
               [.21, .145, .11], "Отдельный водный рукав без ноги и сапога", 6)
        b.oval("water_palm", "skin", [sign*.70, .83, .12], [.13, .13, .115],
               "Раздвоенная водная ладонь, переходящая в три острых когтя", 6)
    b.stage = 2
    b.slot = "head"
    b.loft("water_head", "skin", [[1.87, 0, .01, .09, .09],
                                  [2.03, 0, .045, .16, .15],
                                  [2.28, 0, .01, .235, .19],
                                  [2.47, 0, -.02, .12, .10]],
           "Маскообразная голова воды с острым подбородком и широкой верхней частью", 6)
    for sign in (-1, 1):
        b.plate("water_eye", "accent", [[sign*.08, 2.20, .207],
                                        [sign*.17, 2.25, .19],
                                        [sign*.15, 2.18, .203],
                                        [sign*.095, 2.17, .213]],
                "Белая миндалевидная глазная грань", .02)
    b.plate("nose_ridge", "primary", [[-.03, 2.32, .195], [.03, 2.32, .195],
                                       [0, 2.06, .25]], "Длинный острый центральный гребень водной маски", .025)
    b.stage = 3
    b.slot = "torso"
    b.tube("upper_wave", "accent", [[-.38, 1.66, -.01], [-.36, 1.54, .23],
                                    [-.12, 1.45, .28], [.14, 1.53, .27],
                                    [.40, 1.73, .03], [.30, 1.84, -.03]],
           [.045, .075, .085, .07, .045, .007], "Широкая угловатая волна вокруг грудной клетки", 4)
    b.tube("lower_wave", "skin", [[-.22, .59, .05], [-.20, .74, .18],
                                  [.16, 1.00, .24], [.34, 1.24, .04], [.29, 1.42, -.04]],
           [.018, .065, .075, .06, .007], "Длинная восходящая спираль вокруг сужающегося корпуса", 4)
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_wisp"
        b.tube("arm_wave", "skin", [[sign*.49, 1.49, .10],
                                     [sign*.60, 1.33, .17], [sign*.80, 1.18, .15],
                                     [sign*.70, 1.01, .20], [sign*.66, .87, .21]],
               [.013, .055, .07, .055, .009], "Лента воды обвивает свой отдельный рукав", 4)
    b.stage = 4
    b.slot = "head"
    b.tube("central_crest", "skin", [[0, 2.31, -.02], [-.10, 2.54, -.06],
                                      [-.14, 2.75, -.04], [.02, 2.95, -.025]],
           [.17, .15, .09, .003], "Высокий изогнутый гребень воды над головой", 5)
    for sign in (-1, 1):
        b.tube("side_crest", "skin", [[sign*.17, 2.31, 0], [sign*.28, 2.50, -.035],
                                       [sign*.25, 2.67, -.015]], [.09, .06, .003],
               "Боковой острый водный гребень", 4)
        b.tube("cheek_splash", "primary", [[sign*.18, 2.13, -.01],
                                           [sign*.30, 2.22, -.03], [sign*.34, 2.36, -.02]],
               [.07, .045, .002], "Наружная водная лопасть рядом со скулой", 4)
    b.stage = 5
    for sign, side in ((-1, "left"), (1, "right")):
        b.slot = side+"_wisp"
        for i in range(3):
            x = sign*.70+(i-1)*.09
            b.tube("water_claw", "skin", [[x, .83, .19], [x+(i-1)*.035, .63, .27],
                                           [x+(i-1)*.045, .54+.035*i, .18]],
                   [.047, .032, .002], "Один из трёх крупных сужающихся водных когтей", 4)
        b.plate("floating_droplet", "skin", [[sign*.88, 1.52, .05],
                                             [sign*.98, 1.64, .04], [sign*.92, 1.47, .08]],
                "Отдельная крупная капля у плеча; принадлежит своей части", .06)
    return b.recipe()


RECIPES = {"supreme-summoner": supreme_summoner, "grand-wizard": grand_wizard,
           "mighty-warlock": mighty_warlock, "water-elemental": water_elemental}
