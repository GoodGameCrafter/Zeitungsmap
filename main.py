# -*- coding: utf-8 -*-
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty,StringProperty,NumericProperty
from kivy.uix.gridlayout import GridLayout
from kivymd.app import MDApp
from kivy_garden.mapview import MapMarker,MapView
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.card import MDCard
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import Clock
import os
import certifi
import ssl
import geopy
from geopy.geocoders import Nominatim
ctx = ssl.create_default_context(cafile=certifi.where())    #https überprüfung umgehen
geopy.geocoders.options.default_ssl_context = ctx
import webbrowser
from typing import Any, Callable, Dict, List, Optional, Tuple
import threading
import pandas as pd
import time
from android.permissions import request_permissions, Permission
request_permissions([Permission.INTERNET,Permission.WRITE_EXTERNAL_STORAGE,Permission.READ_EXTERNAL_STORAGE])

class AdressCard(MDCard):
    adresse = StringProperty()
    zeitungsanzahl = StringProperty()
    hinweis = StringProperty()
    width = NumericProperty()
    height = NumericProperty()

class WindowManager(ScreenManager):
    pass

class Seite_1(Screen):
    def __init__(self, **kwargs):
        super(Seite_1, self).__init__(**kwargs)
        self.label = ObjectProperty(None)
        self.textinput = ObjectProperty(None)
        self.textinput_1 = ObjectProperty(None)
        self.textinput_2 = ObjectProperty(None)
        self.checked = False  # wenn check-entry erfolgreich

    def open_url(self):                 #öffnet ausgewählten Link
        webbrowser.open_new_tab("https://www.kbv-vertrieb.de/")

    def check_entry(self):
        file = self.textinput.text
        if not os.path.exists(file) or file == "":
            self.error_popup(f"{self.label.text}\nDateipfad ist ungültig")
            return
        if ".ods" not in file[-5:] and ".xlsx" not in file[-5:]:
            self.error_popup(f"{self.label.text}\nDateiformat wird nicht\nunterstützt! ->(.xlsx,.ods)")
            return
        self.manager.current = "Map"
        self.checked = True

    def read_file(self,filepath: str) -> dict[dict[list[str, str, bool]]]:
        textlines = []  # -> enthält alle zeilen aus Tabelle
        if filepath[-4:] == ".ods":
            ods_df = pd.read_excel(filepath, engine="odf")
        else:
            ods_df = pd.read_excel(filepath, engine='openpyxl')
        headers = []
        for i, line in enumerate(ods_df):  # Erste Zeile des dokuments wird als Überschrift genommen
            headers.append(line)
        for i in range(len(ods_df)):  # Spalte
            line = ""
            for j in range(len(headers)):  # Zeile
                if str(ods_df[headers[j]][i]) != "nan":
                    line += str(ods_df[headers[j]][i]) + " "
            textlines.append(line)

        Straßen = []
        Adressbuch = {}
        for elem in enumerate(textlines):
            temp_adressliste = {}
            sv = elem.strip().split(" ")
            try:
                Straße, Hausnummer, Zeitungen = sv[:3]
            except Exception as e:  # Zeile stellt nicht genug daten zur Verfügung
                continue
            if Straße.upper() == "STRASSE":  # Falls erste Zeile des dokuments leer
                continue
            if Straße not in Straßen:  # erste Straße wird initialisiert
                Straßen.append(Straße)
            try:
                Zeitungen = int(float(Zeitungen))  # Überprüfen ob anzahl der Zeitungen eine Zahl ist
            except Exception as e:
                continue
            try:
                Adressbuch[Straße][Hausnummer] = [str(int(Zeitungen)), sv[3], False]  # Wenn kein Hinweis angegeben
            except:
                Adressbuch[Straße][Hausnummer] = [str(int(Zeitungen)), "--", False]
        return Adressbuch

    def error_popup(self,text:str):
        pop = Popup(title='Fehler',
                    content=Label(text=text,text_size= (self.width*0.7, None),
                    size= self.size,halign= 'center',valign= 'center'),
                    size_hint=(0.7, 0.2))
        pop.open()
class OpenFile(Screen):
    def __init__(self,val:int=None,**kwargs):
        super(OpenFile, self).__init__(**kwargs)
        global Val;Val = val

    def openFile(self,filepath:str, filepathname: str):
            if filepathname != [] :
                self.manager.ids.main.ids.textinput.text = filepathname[0]

class Seite_2(Screen):
    def __init__(self, **kwargs):
        super(Seite_2, self).__init__(**kwargs)
        self.timeout = False
        self.map_initialized = False
        self.loading = False
        self.label = ObjectProperty(None)

    def initMainData(self,Ort:str,PLZ:str,data:dict):
        self.index = 1
        self.Ort = Ort
        self.PLZ = PLZ
        self.data = data
        self.addMap()

    def addMap(self):
        lat, lon = self.adress_to_latlon(f"{self.PLZ},{self.Ort}")
        if lat != None:
            self.map = MapView(size_hint_y=0.6,
                               pos_hint={"x": 0, "top": 0.9},
                               lat=lat, lon=lon,
                               double_tap_zoom=True,
                               zoom=18)
            self.manager.ids.map.ids.map.add_widget(self.map)
            self.grid = GridLayout(rows=1, size_hint=(None, None), spacing=30)
            self.grid.bind(minimum_width=self.grid.setter('width'))
            self.map_initialized = True

    def adress_to_latlon(self,adresse:str) -> Tuple[float, float]:
        init_map = False
        try:
            Hausnummer, Straße, PLZ, Ort = adresse.split(",")               #Suchen einer Adresse
        except Exception as e:
            init_map = True # initialisierung der map
            Hausnummer = None
        geolocator = Nominatim(user_agent="Zeitungsmap")
        try:
            location = geolocator.geocode(adresse+",Deutschland")
            lat, lon = location.latitude, location.longitude
            if str(location).split(",")[0] != Hausnummer and not init_map:
                Clock.schedule_once(lambda dt: self.error_popup(f"Unbekannte Hausnummer: {Straße} {Hausnummer}"),
                                    0.1)
            return lat, lon
        except Exception as e:
            if "'NoneType' object" in str(e):
                Clock.schedule_once(lambda dt: self.error_popup(f"Unbekannte Adresse: {adresse}"), 0.5)
            if "Failed to establish a new connection" in str(e):
                Clock.schedule_once(lambda dt: self.error_popup(f"Verbindung verloren", 40.0), 0.5)
            self.timeout = True
        return None,None

    def error_popup(self, text: str,time:float=1.0):
        pop = Popup(title='Fehler',
                    content=Label(text=text, text_size=(self.width * 0.6, None),
                                  size=self.size, halign='left', valign='center'),
                    size_hint=(0.7, 0.2))
        pop.open()
        Clock.schedule_once(lambda dt: pop.dismiss(),time)

    def add_Dropdown(self,caller):
        data = ["Alle"]+[Straße for Straße in self.data]
        menu_items = [
            {
                "text": f"{elem}",
                "viewclass": "OneLineListItem",
                "height": dp(54),
                "on_release": lambda x=f"Item {elem}": self.menu_callback(x),
            } for elem in data
        ]
        self.menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            position="center",
            width_mult=3,
            border_margin=dp(24)
        )
        self.menu.open()

    def menu_callback(self, text_item: str):
        if self.map_initialized and not self.loading:
            text = text_item.replace("Item", "").strip()
            self.menu.dismiss()
            self.removeWidgets()
            self.addMap()
            t2 = threading.Thread(target=self.setWidgets, args=[text])
            t2.start()

    def setWidgets(self,Straßen:str = "Alle"):
        self.loading = True
        t3 = threading.Thread(target=self.Loading_animation)
        t3.start()
        if Straßen == "Alle":
            Straßen = [Straße for Straße in self.data]
        else:
            Straßen = [Straßen]
        for Straße in Straßen:
            for i, Hausnummer in enumerate(self.data[Straße], start=1):
                adresse = f"{Hausnummer},{Straße},{self.PLZ},{self.Ort}"
                lat, lon = self.adress_to_latlon(adresse)
                if self.timeout:
                    break
                if lat == None:
                    continue
                Clock.schedule_once(lambda dt: self.addCard(adresse), 0.1)
                self.data[Straße][Hausnummer][3:]=[lat,lon]
                if i == 1:
                    self.center_on_marker(lat, lon);
                    self.map.zoom = 16
                if self.data[Straße][Hausnummer][2]:
                    Clock.schedule_once(lambda dt: self.addMarker(lat, lon,"./marker_green.png"), 0.1)
                else:
                    Clock.schedule_once(lambda dt: self.addMarker(lat, lon), 0.1)
                time.sleep(0.2) # delay um clock zeit zum ausführen zu geben
        Clock.schedule_once(lambda dt:self.manager.ids.map.ids.scroll_box.add_widget(self.grid),0.1)
        self.loading = False
        self.label.text = "Bitte Straße auswählen"

    def addMarker(self,lat:float,lon:float,source:str = "default"):
        if source == "default":
            marker = MapMarker(lat=lat, lon=lon)
        else:
            marker = MapMarker(lat=lat, lon=lon,source = source)
        marker.on_press()
        self.map.order_marker_by_latitude = False
        self.map.add_marker(marker)

    def addCard(self,adresse:str):
        Hausnummer,Straße = adresse.split(",")[:2]
        zeitungsanzahl,hinweis,check = self.data[Straße][Hausnummer][:3]
        card = AdressCard()
        card.adresse = f"{Straße} {Hausnummer}, " +adresse.split(",",2)[2]
        card.zeitungsanzahl = zeitungsanzahl
        card.hinweis = hinweis
        if check:
            card.ids.check.state = "down"
        card.width = int(self.manager.ids.map.ids.scroll_box.width*0.97)
        card.height = int(self.manager.ids.map.ids.scroll_box.height)
        self.grid.add_widget(card)

    def center_on_marker(self,lat:float,lon:float):
        self.map.center_on(lat,lon)  # zentrieren auf marker

    def select_index(self,opp:str):
        if not len(self.grid.children) or self.loading:
            return
        if opp == "+":
            self.index += 1
        else:
            self.index -= 1
        self.index = max(1, min(self.index, len(self.grid.children)))
        self.scroll_widgets(self.index)

    def scroll_widgets(self, index: int):
        widget = self.grid.children[-index]
        Straße,Hausnummer = widget.adresse.split(",",1)[0].split(" ")
        ## center on marker
        lat, lon = self.data[Straße][Hausnummer][3:]
        self.center_on_marker(lat,lon);self.map.zoom = 19
        ### scroll to correct card
        widget.pos[1] = 0  # animation setzt y koordinate auf -50?!
        self.manager.ids.map.ids.scroll_box.scroll_to(widget, padding=10, animate=True)

    def change_marker(self,state:str,adresse:str):
        Straße, Hausnummer = adresse.split(",", 1)[0].split(" ")
        lat, lon = self.data[Straße][Hausnummer][3:]
        for marker in self.map.children[0].children:
            if lat == marker.lat and lon == marker.lon:
                self.data[Straße][Hausnummer][2] = False
                marker.source = "./marker_red.png"
                if state == "down":
                    self.data[Straße][Hausnummer][2] = True
                    marker.source = "./marker_green.png"
                break

    def update(self):
        if not self.loading:
            self.removeWidgets()
            self.addMap()

    def removeWidgets(self):
        self.timeout = False
        self.loading = False
        self.map_initialized = False
        self.index = 1
        self.label.text = "Bitte Straße auswählen"
        try:
            self.manager.ids.map.ids.map.remove_widget(self.map)
            self.manager.ids.map.ids.scroll_box.remove_widget(self.grid)
        except:
            None

    def Loading_animation(self):
        while self.loading:
            for elem in ["\\", "|", "/", "-"]:
                self.label.text = f"\rLädt: {elem}"
                time.sleep(0.25)

class Zeitungsmap(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        Builder.load_file("main.kv")
        return WindowManager()

    def change_screen(self, screen: str):
        self.root.current = screen
        self.root.ids.main.ids.button.disabled = False

if __name__ == "__main__":
    Zeitungsmap().run()