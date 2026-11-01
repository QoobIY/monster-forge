"""Palette choices whose current thumbnails are stored as static constructor assets."""
from .constructor_atlas import COLORWAYS
from .constructor_decor import colorways

MATERIAL_NAMES=('Олива и золото','Бургундия','Синий дозор','Песок и бронза','Графит',
                'Слива','Кремовый и лазурь','Бирюза и коралл','Терракота','Ледяное серебро')

def options():
    return [{'id':'original','label':'Исходные цвета','colors':{}},
            *[{'id':'palette-'+p['id'],'label':p['label'],'colors':p['colors']} for p in colorways()],
            *[{'id':'material-'+str(n),'label':MATERIAL_NAMES[n-1],
               'colors':dict(zip(('cloth','accent','metal','leather'),('#'+c for c in colors)))}
              for n,colors in enumerate(COLORWAYS,1)]]
