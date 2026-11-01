"""Versioned semantic catalogue for AI selection and generation guidance."""
import json
from functools import lru_cache
from .paths import ROOT

PATH=ROOT/'config/constructor_part_descriptions_v7.json'

NAMES={
 'male_faces':'Широкое квадратное лицо|Удлинённое узкое лицо|Округлое полное лицо|Ромбовидное лицо|Сердцевидное лицо|Прямоугольное лицо|Широкая нижняя челюсть|Овальное лицо|Худое узкое лицо|Сильное лицо с широким подбородком',
 'female_faces':'Широкое квадратное лицо|Удлинённое узкое лицо|Округлое лицо|Ромбовидное лицо|Сердцевидное лицо|Мягкое прямоугольное лицо|Широкая нижняя челюсть|Овальное лицо|Худое узкое лицо|Широкие скулы и подбородок',
 'hair':'Короткие пряди набок|Каре с мягкой косой чёлкой|Высокий объёмный хвост|Две длинные косы|Объёмные крупные кудри|Ирокез с тремя острыми прядями|Округлое афро|Длинные прямые волосы|Плетение вокруг макушки|Толстые дреды|Короткий кроп с короткой чёлкой|Боковой пробор с широкими прядями|Зачёс назад с продольными прядями|Короткие кудри на макушке|Низкий затылочный пучок|Пикси с косой чёлкой|Волнистое каре до плеч|Две свисающие плетёные косы|Два верхних боковых пучка|Коса вокруг головы с затылочным пучком|Короткая стрижка с фейдом|Объёмный квифф|Шторки с центральным пробором|Небрежная стрижка до ушей|Воин · собранные длинные волосы|Длинные волны с пробором|Высокий хвост с чёлкой|Боковая плетёная коса|Французское каре|Плетёный низкий пучок',
 'ears':'Небольшие человеческие уши с округлым завитком|Крупные широкие человеческие уши|Длинные заострённые эльфийские уши|Широкие заострённые орочьи уши|Высокие вертикальные волчьи уши|Удлинённые свисающие уши|Большие веерообразные слоновьи уши|Фигурные плавниковые уши|Лопастные перепончатые уши|Человеческие уши с выемкой в крае',
 'noses':'Компактный нос с округлым кончиком|Узкий вытянутый нос с изгибом переносицы|Широкий нос с крупными крыльями|Короткий нос с небольшим выступанием|Узкий выступающий нос с опущенным кончиком|Нос с приподнятым кончиком|Тонкий длинный нос с низким кончиком|Широкий плоский нос|Широкий нос со средней глубиной|Смещённый в сторону широкий нос',
 'brows':'Толстые брови|Тонкие брови|Угловатые брови|Прямые брови|Дугообразные брови|Низкие брови|Высокие брови|Брови с разрывом|Неравномерные брови|Широкие растрёпанные брови',
 'eyes':'Открытые округлые глаза|Узкие глаза|Миндалевидные глаза|Широкие овальные глаза|Наклонённые глаза|Глаза с тяжёлым веком|Маленькие глаза|Большие глаза|Угловатые глазные проёмы|Неравномерные глазные проёмы',
 'jaws':'Широкая челюсть|Узкая челюсть|Умеренно округлая челюсть|Сильно суженная челюсть|Тяжёлая широкая челюсть|Удлинённая узкая челюсть|Короткая широкая челюсть|Умеренно узкая челюсть|Худая челюсть|Широкий подбородок',
 'mouths':'Полные губы|Тонкие губы|Широкий рот|Сдержанный рот|Лёгкая улыбка|Кривой рот|Рот со шрамом|Рот с клыками|Видимые верхние зубы|Приоткрытая улыбка с верхними и нижними зубами',
 'beards':'Короткая геометрическая щетина|Короткая прямоугольная борода|Полная борода с боковыми объёмами|Длинная широкая борода|Заострённая борода|Раздвоенная борода|Толстая плетёная борода|Узкая бородка на подбородке|Узкие фигурные бакенбарды|Широкие бакенбарды по челюсти',
 'mustaches':'Тонкие усы|Толстые прямые усы|Усы с поднятыми концами|Подковообразные усы|Широкие нависающие усы|Усы из двух раздельных половин|Плетёные кончики усов|Закрученные вверх концы|Короткие компактные усы|Усы с поднятыми концами, второй вариант',
 'race_heads':'Человеческая голова|Эльфийская голова|Орочья голова|Голова минотавра|Волчья голова|Скелетный череп|Ангельская голова|Демоническая голова|Голова кабанолюда|Голова слонолюда',
 'body_forms':'Узкий силуэт, ширина 88%|Силуэт шириной 103%|Широкий силуэт, 110%|Очень широкий силуэт, 120%|Слегка узкий силуэт, 94%|Стройный силуэт, 86%|Силуэт шириной 98%|Широкий силуэт, 112%|Очень узкий силуэт, 80%|Полный силуэт, 118%',
 'male_clothes':'Синяя стражницкая туника с нагрудником и табардом|Светлый капитанский доспех|Бирюзовый длинный кафтан мага|Фиолетовое пальто чародея|Зелёный охотничий жилет с диагональным ремнём|Рабочая туника с кожаным фартуком|Бордовый королевский кафтан|Светлая гражданская туника|Песочное одеяние с запахом и накидкой|Синяя зимняя куртка с меховой отделкой',
 'female_clothes':'Светлый рыцарский доспех с раздельными нижними панелями|Бирюзовое одеяние мага|Фиолетовое длинное одеяние чародейки|Зелёный охотничий костюм|Рабочий костюм с фартуком|Синее королевское одеяние с золотой отделкой|Светлая гражданская туника|Терракотовое одеяние с запахом|Синий стражницкий костюм|Синее зимнее пальто',
 'arms':'Светлый тканевый рукав с манжетой|Рука с пластинчатой защитой|Рука с перекрывающимися пластинами|Открытая мускулистая рука|Расширенный рукав мага|Прилегающий охотничий рукав|Утеплённый рукав с меховой манжетой|Королевский рукав с крупной отделкой|Костяная рука|Каменная рука с гранёной кистью',
 'legs':'Простые брюки и обувь|Нога с доспехом|Нога мага с тканевой боковой панелью|Охотничья нога с кожаными обмотками|Рабочая нога с широкими обмотками|Королевская нога с защитой голени|Зимняя нога с меховой отделкой|Открытая зелёная орочья нога|Костяная нога|Тёмная широкая стопа на массивной ноге',
 'gloves':'Открытая человеческая кисть|Кожаная перчатка без пальцев|Зелёная охотничья перчатка|Стальная латная перчатка|Латунная латная перчатка|Тканевая перчатка мага|Рабочая перчатка с накладками|Зелёная орочья кисть|Костяная кисть|Каменная бронированная кисть',
 'boots':'Низкая гражданская обувь|Высокий охотничий сапог|Бронированный сапог|Утеплённый рабочий сапог|Мягкая обувь мага|Высокий королевский сапог|Меховой зимний сапог|Открытая орочья стопа|Костяная стопа|Широкая тёмная стопа',
 'shoulders':'Гранёная пластина|Три перекрывающиеся пластины|Рога на плечевой основе|Шипы на плечевой основе|Крупные перья|Объёмный мех|Гранёные кристаллы|Плечевые свитки|Крыловидный наплечник|Один наплечник с левой стороны',
 'belts':'Кожаный пояс с полой пряжкой|Пояс с парными подсумками|Пояс с инструментами|Пояс с цепью|Пояс с камнями в оправах|Тканевый кушак со свисающим концом|Двойной пояс|Пояс с флаконами|Пояс со свитками|Пояс с книгой и застёжкой',
 'headwear':'Обруч с камнем|Корона с выступающими зубцами|Диадема с дугами|Очки с оправой и ремнём|Парные серьги|Перо с выраженным стержнем|Камень на лбу в оправе|Парные накладки на рога|Лавровый венок|Полумаска',
 'emblems':'Львиная голова с гривой|Солнце с двенадцатью лучами|Полумесяц|Звезда|Череп|Лист с прожилками|Молния|Раскрытые крылья|Гранёный ромбовидный камень|Изогнутая змея',
 'back':'Короткий раздельный плащ|Длинный королевский плащ|Двухслойная накидка|Парные перьевые крылья|Парные перепончатые крылья|Парные кристаллические крылья|Рюкзак со спальником и ремнями|Колчан со стрелами|Спинная броня с шипами|Знамя с поперечиной и подвесами',
 'accessories':'Подвесная книга|Набор из трёх флаконов|Набор из трёх свитков|Подвесной молоток|Фонарь с каркасом|Парные роговые трофеи|Кристаллический амулет|Подсумок с ножом|Круглый компас|Фляга с крышкой',
 'patterns':'Кант с ромбами|Рунная цепь|Солнечные знаки|Переплетение|Ветви и листья|Двойной шеврон|Созвездия|Вертикальные руны|Алхимические печати|Чешуйчатый орнамент',
 'colorways':'Зелёная ткань, светлая отделка, латунь, коричневая кожа|Бордовая ткань, золото, сталь, тёмная кожа|Синяя ткань, светлая отделка, сталь, тёмная кожа|Песочная ткань, кремовая отделка, медь, светлая кожа|Тёмная ткань, медная отделка, сталь, тёмная кожа|Фиолетовая ткань, светлая отделка, серебро, коричневая кожа|Светлая ткань, синяя отделка, золото, светлая кожа|Бирюзовая ткань, коралловая отделка, бронза, коричневая кожа|Рыжая ткань, бирюзовая отделка, медь, тёмная кожа|Ледяная синяя ткань, светлая отделка, серебро, серая кожа',
}

RULES={
 'hair':'Основание повторяет плоскости выбранного черепа и закрывает затылок. Пряди соединяются с основанием; косы и хвосты свободно свисают. Крупные объёмы вместо отдельных волосков. Украшения не заменяют волосы.',
 'ears':'Парная ушная раковина с объёмным краем, углублённой чашей и креплением к боковой поверхности головы. Форму края, длину и направление менять независимо от формы лица.',
 'noses':'Объёмная переносица, плавный переход к кончику, два крыла и отдельные ноздри. Основание прилегает к лицу; ширина, выступание и высота кончика различаются независимо.',
 'male_faces':'Контуры орбит, скул, щёк и нижней челюсти образуют осмысленные плоскости. Полный округлый затылок; короткая шея. Глаза, рот, нос и уши выбираются отдельно.',
 'female_faces':'Взрослые пропорции лица; форма лба, скул и подбородка различается. Полный затылок и короткая шея. Черты лица и причёска выбираются отдельно.',
 'jaws':'Меняется только нижняя часть лица: ширина челюсти и длина подбородка. Верх лица, орбиты и форма лба остаются выбранными отдельно.',
 'eyes':'Парные проёмы с верхним и нижним веком, радужкой и зрачком. Глаза лежат на поверхности выбранного лица; цвет радужки независим от формы.',
 'brows':'Парные объёмные полосы на поверхности лба. Различаются толщина, дуга, высота и наклон; не заменяют волосы или глаза.',
 'mouths':'Губы повторяют поверхность нижней части лица. Сохранять изгиб верхней губы и объём нижней. Видимые зубы — отдельные коронки; орочьи клыки имеют собственную анатомию.',
 'beards':'Борода крепится к подбородку и бокам нижней челюсти. Различать щетину, боковые объёмы, кончик и плетение. Не закрывать рот сплошной пластиной.',
 'mustaches':'Усы крепятся над верхней губой, состоят из двух читаемых половин. Центральный просвет, концы и направление отличаются; борода выбирается отдельно.',
 'arms':'Отдельные левая и правая руки: плечо, локоть, предплечье и кисть с большим пальцем и пальцами. Сохранять анатомические сужения и округлое плечевое основание.',
 'legs':'Отдельные левая и правая ноги: бедро, колено, длинная голень и стопа. Колено направлено вперёд, ноги не выгнуты внутрь; стопы стоят на общей плоскости.',
 'gloves':'Отдельные объёмы ладони, большого пальца и пальцев. Манжета принадлежит одежде; кисть прикрепляется к запястью выбранной руки.',
 'boots':'Форма носка, пятки и голенища читается в силуэте. Сохранять масштаб ноги и общую плоскость подошв; не растягивать обувь независимо.',
 'shoulders':'Наплечник крепится к верхней части выбранной руки. Объёмную защиту сохранять объёмной, плоские накладки прижимать к основе. Выбор 0 означает отсутствие всех наплечников.',
 'headwear':'Посадка учитывает выбранный череп и внешний объём причёски. Обруч охватывает волосы; корона, камни, дуги диадемы и листья венка остаются снаружи прядей и сохраняют общий каркас. Волосы не удаляются. Серьги крепятся около ушей, очки сохраняют посадку на лице.',
 'emblems':'Неглубокий объёмный рельеф на поверхности выбранного нагрудника. Основание прилегает к одежде, форма символа и цвет отделки выбираются отдельно.',
 'belts':'Пояс следует объёму талии. Пряжка имеет отверстие и язычок; подсумки, ремни и застёжки имеют читаемые крепления к поясу.',
 'back':'Отдельная часть back_attachment. Плащи начинаются у верхней спины; рюкзак, спальник, колчан и знамя имеют крепления. Крылья имеют основания и основные структурные объёмы.',
 'accessories':'Компактный подвесной предмет с держателем, петлёй или ремнём. Его крепление соприкасается с поясом или одеждой; элементы предмета соединены между собой.',
 'patterns':'Один крупный знак на груди и отдельные крупные знаки на рукавах, нижних панелях одежды и штанинах. Широкие линии вместо сетки мелких символов. Рисунок прилегает к поверхности каждого модуля; цвет независим от ткани.',
 'body_forms':'Только поперечная ширина модулей: рост и длины конечностей не меняются. Положение коленей и общая плоскость стоп сохраняются.',
 'colorways':'Меняются только цвета ткани, отделки, металла и кожи. Геометрия, силуэт и выбранные детали сохраняются.',
 'male_clothes':'Одежда состоит из независимых торса, рук и ног. Пластины прилегают к основе, отделка — к ткани. Наличие наплечников определяется отдельным выбором.',
 'female_clothes':'Одежда состоит из независимых торса, рук и ног. Сохранять взрослые пропорции и функциональные панели. Декор и наплечники выбираются отдельно.',
 'race_heads':'Сохранять анатомию расы: профиль морды, вид ушей, челюсть и зубы. Человеческая форма лица не заменяет звериную морду.',
}

@lru_cache(maxsize=1)
def catalogue():
    data=json.loads(PATH.read_text())
    if data.get('schema_version') not in {1,2}:raise ValueError('Unsupported part description schema')
    expected={(k,n) for k,names in NAMES.items() for n in range(1,len(names.split('|'))+1)}
    items=data.get('parts',[])
    actual={(e['category'],e['variant']) for e in items}
    if actual!=expected or len(items)!=len(expected):raise ValueError('Incomplete or duplicate part descriptions')
    return data

def summaries():
    result={category:{str(e['variant']):e['description_ru'] for e in catalogue()['parts'] if e['category']==category} for category in NAMES}
    from .constructor_atlas import load
    for n in (2,*range(21,31)):result['hair'][str(n)]=load('hair',n)['attribute_reference']['description_ru']
    from .constructor_armor_details import SHOULDERS,BELTS,SHOULDER_DESCRIPTIONS,BELT_DESCRIPTIONS
    for category,variants,descriptions in [('shoulders',SHOULDERS,SHOULDER_DESCRIPTIONS),('belts',BELTS,BELT_DESCRIPTIONS)]:
        result[category].update({str(n):descriptions[k] for n,k in enumerate(variants,1)})
    from .constructor_head_accessories import DETAILS
    result['headwear'].update({str(n):d for n,d in enumerate(DETAILS,1)})
    return result

def selected(settings,slot):
    if settings['race']=='randomium':
        from .constructor_randomiums import DESIGNS
        field='face' if slot=='head' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else 'outfit'
        design=next(d for d in DESIGNS if d['id']==settings[field])
        return {'schema_version':1,'slot':slot,'race':'randomium','contract':'humanoid_v1',
                'description_ru':design['description_ru']+' Модуль '+slot+'.','parts':[]}
    from .constructor_expansion import ALL
    field='face' if slot=='head' else 'arms' if slot.endswith('_arm') or slot.startswith('front_') else 'legs' if slot.endswith('_leg') or '_leg_' in slot else 'outfit'
    design=next((d for d in ALL if d['id']==settings[field]),None)
    if design:return {'schema_version':1,'slot':slot,'race':settings['race'],'contract':design['contract'],'description_ru':design['description_ru']+' Модуль '+slot+'.','parts':[]}
    from .constructor_flyers import DESIGNS as flyers, SPECIES as flyer_species, part_description
    if settings['race'] in flyer_species:
        donor=settings['outfit']
        if slot=='head':donor=settings['face']
        elif slot.endswith('_wing'):donor=settings['back'] or (settings['arms'] if settings['race']=='sky-eagle' else settings['outfit'])
        elif slot.startswith('front_'):donor=settings['arms']
        elif slot.endswith('_leg'):donor=settings['legs']
        design=next(d for d in flyers if d['id']==donor)
        return {'schema_version':1,'slot':slot,'race':settings['race'],'contract':design['contract'],'pose':'flight','description_ru':part_description(design,slot),'parts':[]}
    descriptions={'head':'Голова выбранной расы с отдельными чертами лица, волосами и украшениями; полный затылок и короткая шея.',
        'torso':'Торс с выбранной одеждой, короткой шеей, поясом, эмблемой и узором.',
        'left_arm':'Левая рука: округлое плечевое основание, локоть, предплечье, запястье и кисть.',
        'right_arm':'Правая рука: округлое плечевое основание, локоть, предплечье, запястье и кисть.',
        'left_leg':'Левая нога: бедро, колено вперёд, длинная голень, стопа на общей плоскости.',
        'right_leg':'Правая нога: бедро, колено вперёд, длинная голень, стопа на общей плоскости.',
        'back_attachment':'Отдельное крепление спины: плащ, крылья, рюкзак, колчан, броня или знамя.'}
    parts=[e for e in catalogue()['parts'] if settings['reference_parts'].get(e['category'])==e['variant'] and slot in e['affected_slots']]
    from .constructor_helmets import DESCRIPTIONS
    additions=[]
    from .constructor_faceless import DESCRIPTIONS as faceless_descriptions
    if slot=='head' and settings['decor']['headwear'] in faceless_descriptions:
        k=settings['decor']['headwear'];additions.append(('decor.headwear',k,faceless_descriptions[k]))
    if slot=='head' and settings['reference_parts']['headwear']:
        from .constructor_head_accessories import DETAILS
        n=settings['reference_parts']['headwear'];parts=[p for p in parts if p['category']!='headwear']
        additions.append(('reference_parts.headwear','refined-headwear-'+str(n),DETAILS[n-1]))
    from .constructor_goblins import DESCRIPTIONS as goblin_descriptions,GLOVES as goblin_gloves,BOOTS as goblin_boots
    if settings['race']=='goblin':
        parts=[p for p in parts if p['category'] not in {'gloves','boots'}]
        if slot.endswith('_arm'):
            n=settings['reference_parts']['gloves'] or 1
            additions.append(('reference_parts.gloves','goblin-gloves-'+str(n),goblin_gloves[n-1]+'. Самостоятельная кисть гоблина: четыре пальца, большой палец и открытые зелёные кончики; крепление к SDK запястью.'))
        if slot.endswith('_leg'):
            n=settings['reference_parts']['boots'] or 1
            additions.append(('reference_parts.boots','goblin-boots-'+str(n),goblin_boots[n-1]+'. Самостоятельная обувь гоблина: пятка, голенище, ремни и загнутый вверх носок; подошва Y=0.'))
    goblin_field='outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else 'back' if slot=='back_attachment' else None
    if goblin_field and settings[goblin_field] in goblin_descriptions:
        k=settings[goblin_field];additions.append((goblin_field,k,goblin_descriptions[k]))
    if slot=='head' and settings['decor']['headwear'] in goblin_descriptions:
        k=settings['decor']['headwear'];additions.append(('decor.headwear',k,goblin_descriptions[k]))
    from .constructor_armor_details import SHOULDER_DESCRIPTIONS,BELT_DESCRIPTIONS,SHOULDERS as armor_shoulders,BELTS as armor_belts
    armor_category='shoulders' if slot.endswith('_arm') else 'belts' if slot=='torso' else None
    if armor_category:
        armor_descriptions=SHOULDER_DESCRIPTIONS if armor_category=='shoulders' else BELT_DESCRIPTIONS
        n=settings['reference_parts'][armor_category]
        k=(armor_shoulders if armor_category=='shoulders' else armor_belts)[n-1] if n else settings['decor']['shoulders' if armor_category=='shoulders' else 'belt']
        if k in armor_descriptions:additions.append(('reference_parts.'+armor_category if n else 'decor.'+('shoulders' if armor_category=='shoulders' else 'belt'),'refined-'+armor_category+'-'+k,armor_descriptions[k]))
    from .constructor_physiques import DESCRIPTIONS as physique_descriptions
    if slot in {'torso','left_arm','right_arm','left_leg','right_leg'} and settings['form'] in physique_descriptions:
        additions.append(('form',settings['form'],physique_descriptions[settings['form']]))
    if slot=='head' and not settings['reference_parts']['headwear'] and settings['decor']['headwear'] in DESCRIPTIONS:
        k=settings['decor']['headwear'];additions.append(('decor.headwear',k,DESCRIPTIONS[k]))
    rune_descriptions={'ancient_runes':'Крупные угловатые древние руны с парными боковыми штрихами.',
        'elven_runes':'Крупные эльфийские руны с изогнутыми стержнями и листовидными петлями.',
        'demonic_runes':'Крупные демонические сигилы с рогами, крюками и острыми клиньями.'}
    from .constructor_elemental_runes import ELEMENTS
    rune_descriptions.update({k:e['description'] for k,e in ELEMENTS.items()})
    if slot in {'torso','left_arm','right_arm','left_leg','right_leg'} and not settings['reference_parts']['patterns'] and settings['decor']['pattern'] in rune_descriptions:
        k=settings['decor']['pattern'];additions.append(('decor.pattern',k,rune_descriptions[k]+' Ленты следуют каждой грани ткани, без пересечения пустых швов.'))
    back_descriptions={'back-angel-large':'Большие парные ангельские крылья: размах около трёх метров, три ряда перекрывающихся перьев и отдельные стержни.',
        'back-demon-large':'Большие парные демонические крылья: размах около трёх метров, перепонки со вогнутыми краями, объёмные пальцы и загнутые когти на концах.',
        'back-raven':'Вороньи крылья: тёмное объёмное оперение, согнутое плечо и предплечье, семь раздельных маховых перьев разной длины, восемь вторичных и два перекрывающихся ряда кроющих перьев на каждой стороне.'}
    from tools.creature_workshop.celestial_wings import DESCRIPTIONS as wing_descriptions
    back_descriptions.update(wing_descriptions)
    from .constructor_emblems import DESCRIPTIONS as emblem_descriptions
    if slot=='torso' and not settings['reference_parts']['emblems'] and settings['decor']['emblem'] in emblem_descriptions:
        k=settings['decor']['emblem'];additions.append(('decor.emblem',k,emblem_descriptions[k]))
    from .constructor_costumes import DESCRIPTIONS as costume_descriptions
    field='outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else None
    if field and settings[field] in costume_descriptions:
        k=settings[field];additions.append((field,k,costume_descriptions[k]))
    if slot=='back_attachment' and settings['back'] in back_descriptions and not settings['reference_parts']['back']:
        k=settings['back'];additions.append(('back',k,back_descriptions[k]))
    from .constructor_owned_races import DESIGNS as OWNED_DESIGNS
    own=next((d for d in OWNED_DESIGNS if d['id']==settings['face']),None)
    if settings['race']=='ghost':
        from .constructor_ghosts import FACES as GHOST_FACES, COSTUMES as GHOST_COSTUMES
        ghost_field='face' if slot=='head' else 'outfit' if slot=='torso' else 'arms' if slot.endswith('_arm') else 'legs' if slot.endswith('_leg') else None
        if ghost_field:
            ghost=next(d for d in OWNED_DESIGNS if d['id']==settings[ghost_field])
            detail=(GHOST_FACES if slot=='head' else GHOST_COSTUMES)[ghost['variant']]
            if slot.endswith('_leg') and settings['form']=='ghost_spirit':
                from .constructor_ghosts import SPIRIT_DESCRIPTION
                detail=SPIRIT_DESCRIPTION
            if slot.endswith('_arm'):
                detail+=' Анатомия руки как у человека: дельта, бицепс, трицепс, локоть и сужающееся предплечье; единая кисть с костяшками, четырьмя пальцами и отдельным большим пальцем с общей сеткой у основания.'
            additions.append((ghost_field,ghost['id'],detail+' Отдельная модульная часть на контракте humanoid_v1.'))
    from .constructor_wild_clothes import SHOULDERS as WS, BELTS as WB
    if slot.endswith('_arm') and settings['decor']['shoulders'] in WS:
        k=settings['decor']['shoulders'];additions.append(('decor.shoulders',k,WS[k]+'; подогнано по поверхности расовой руки.'))
    if (slot=='torso' or slot.endswith('_leg')) and settings['decor']['belt'] in WB:
        k=settings['decor']['belt'];additions.append(('decor.belt',k,WB[k]+'; по форме расовых бёдер и ног.'))
    if slot=='head' and settings['race'] in {'beorn','panda'}:
        from .constructor_bear_mouths import DEFAULTS,DESCRIPTIONS
        kind=settings['features']['mouth'];kind=DEFAULTS[own['variant']] if kind in {'profile','original'} else kind
        additions.append(('features.mouth',kind,DESCRIPTIONS[kind]))
    if own and own['race']!='ghost':
        detail=own['description_ru']
        if slot=='head' and own['race']=='golem':
            from .constructor_golem_faces import DESCRIPTIONS as GOLEM_FACE_DESCRIPTIONS
            detail=GOLEM_FACE_DESCRIPTIONS[own['variant']]
        additions.append(('face',own['id'],detail))
        from .constructor_owned_pelts import DESCRIPTIONS as PELT_DESCRIPTIONS
        if own['race'] in PELT_DESCRIPTIONS:
            additions.append(('race.pelt','owned-pelt-v3',PELT_DESCRIPTIONS[own['race']]))
    from .constructor_racial_anatomy import VARIANTS
    if settings['face'] in VARIANTS:
        additions.append(('face',settings['face'],VARIANTS[settings['face']]['description_ru']))
    parts.extend({'id':k,'description_ru':d,'generation_prompt_ru':d+' '+catalogue()['style_profile']['geometry_rules'],
        'selection':{'field':field,'value':k},'affected_slots':[slot]} for field,k,d in additions)
    if settings['race']=='ghost' and settings['form']=='ghost_spirit' and slot.endswith('_leg'):
        descriptions[slot]=('Левая' if slot.startswith('left') else 'Правая')+' составная половина призрачного шлейфа; ног, коленей и ступней нет.'
    return {'schema_version':1,'slot':slot,'contract':'humanoid_v1','description_ru':descriptions[slot],'race':settings['race'],'gender':settings['gender'],'parts':parts}
