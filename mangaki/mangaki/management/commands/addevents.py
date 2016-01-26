from django.core.management.base import BaseCommand, CommandError
from irl.models import Event, Location
from mangaki.models import Anime

from datetime import datetime

class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        anime_ids = {'ARRIETTY, LE PETIT MONDE DES CHAPARDEURS': 2591,
                    'LA COLLINE AUX COQUELICOTS': 8153,
                    'LE CHÂTEAU AMBULANT': 53,
                    'LE ROYAUME DES CHATS': 3315,
                    'LE VENT SE LEVE': 958,
                    'LE VOYAGE DE CHIHIRO': 30,
                    'LES CONTES DE TERREMER': 2461,
                    'MES VOISINS LES YAMADA': 3177,
                    'MON VOISIN TOTORO': 106,
                    'PONYO SUR LA FALAISE': 1563,
                    'PORCO ROSSO': 410,
                    'PRINCESSE MONONOKE': 60}
        
        with open('data/events.txt') as f:
            for line in f:
                date, title, place, language = line.strip().split(' ; ')
                
                date = datetime.strptime(date, "%Y-%m-%d %H:%M")
                fauvettes = Location.objects.get(id=1)
                
                anime = Anime.objects.get(id=anime_ids[title])
                
                Event(date=date, anime=anime, location=fauvettes, event_type="screening", language='vostfr' if language == 'VOST' else 'vf').save()