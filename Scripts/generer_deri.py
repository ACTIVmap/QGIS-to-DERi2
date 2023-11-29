# Layers

edges = QgsProject.instance().mapLayersByName('edges')[0]
nodes = QgsProject.instance().mapLayersByName('nodes')[0]

  ########################
 # Text generation part #
########################

#
# Text generation function
#

def textGeneration(feature):
    
    def shopHandling(feature, txt):
        day_correspondance = {
            "Mo":"Lundi",
            "Tu":"Mardi",
            "We":"Mercredi",
            "Th":"Jeudi",
            "Fr":"Vendredi",
            "Sa":"Samedi",
            "Su":"Dimanche"
        }
        if feature["name"]:
            txt += str(feature["name"]) + " "
            # Hack pour éviter répétition du premier mot
            if txt.split(' ')[0] == txt.split(' ')[1]: txt = ' '.join(txt.split(' ')[1:])
        else:
            txt += "qui n'a pas de nom. "
        if feature["opening_hours"]:
            horaires = feature["opening_hours"]
            for day in day_correspondance:
                horaires = horaires.replace(day+"-", day_correspondance[day]+" au ")
                horaires = horaires.replace(day, day_correspondance[day])
                horaires = horaires.replace("-"," à ")
            horaires = "Horaires d'ouverture: "+horaires
            txt = txt[0:-1] + ". " + horaires
        return txt
    
    txt = ""
    if(feature["txt"]):
        txt += feature["txt"]
    elif(feature["amenity"] == "restaurant"):
        txt += "Restaurant "
        txt = shopHandling(feature, txt)
    elif(feature["amenity"] == "fast_food"):
        txt += "Fast food "
        txt = shopHandling(feature, txt)
    elif(feature["amenity"] == "bank"):
        txt += "Banque "
        txt = shopHandling(feature, txt)
    elif(feature.attribute("amenity") == "bar"):
        txt += "Bar "
        txt = shopHandling(feature, txt)
    elif(feature["amenity"] == "pharmacy"):
        txt += "Pharmacie "
        txt = shopHandling(feature, txt)
    elif(feature["shop"]):
        txt += "Commerce "
        txt = shopHandling(feature, txt)
    elif(feature["highway"] == "bus_stop"):
        txt += "Arret de bus "
        if feature["name"]: txt += feature["name"]+". "
        else: txt += "sans nom. "
    elif(feature["highway"] == "crossing"):
        txt += "Passage piéton "
        if feature["highway"] == "yes": txt += "avec bandes d'éveil de vigilance."
        else: txt += "sans bandes d'éveil de vigilance."
    elif(feature["addr:housenumber"]):
        txt += "Numéro "+feature["addr:housenumber"]
    elif feature["id"].split('_')[0] in ["start", "end"]:
        poi = feature["id"].split('_')
        if poi[0] == "start": txt += "Début de la branche "+poi[1]
        else: txt += "Fin de la branche "+poi[1];
        if poi[2] == "left": txt += " coté gauche."
        else: txt += " coté droit."
    else:
        # POI non-pris en charge
        txt = "POI non-pris en charge."

    return txt

#
# Add text to every POI node
#

with edit(nodes):
    nodes.addAttribute(QgsField("txt",  QVariant.String))
    for feature in nodes.getFeatures():
        feature['txt'] = textGeneration(feature)
        nodes.updateFeature(feature)

  ########################
 # DERi file generation #
########################

import os
import json
from PIL import Image

# Path to the DERi files
path = "/Users/jeremy/Developpement/PoC/"

# Read Configuration file
config = None
with open(os.path.join(path,"configuration.json")) as config_file:
    config = json.load(config_file)
    
# Read image resolution
width, height = PIL.Image.open(os.path.join(path,config["image"])).size

# Create base DERi JSON
deri = {
    "title": config["title"],
    "version": config["version"],
    "imagePath": config["image"],
    "areas": {}
}

# Create areas
layers = {}
for i, interaction in enumerate(config["interactions"]):
    deri["areas"]["area-%s"%i] = {
        "geometry": {
            "shape":config["shape"][0],
            "x": (interaction["location"][0]/width)*100,
            "y": (interaction["location"][1]/height)*100,
            "width": (config["shape"][1]/width)*100,
            "height": (config["shape"][2]/height)*100,
        },
        "interactions": {
            "automatic":interaction["resource"]
        }
    }
    if interaction["layer"] in layers: layers[interaction["layer"]]+=["area-%s"%i]
    else: layers[interaction["layer"]]=["area-%s"%i]

# Create resources
deri["Resource"] = {}
for node in nodes.getFeatures():
    deri["Resource"][node["id"]] = {
        "type":"tts",
        "source":feature["txt"],
        "interactions":{}
    }    
for edge in edges.getFeatures():
    start_node = edge['start']
    end_node = edge['end']
    start_node = nodes.getFeatures(QgsFeatureRequest().setFilterExpression('"id" = \'%s\''%(start_node))).__next__()
    end_node   = nodes.getFeatures(QgsFeatureRequest().setFilterExpression('"id" = \'%s\''%(end_node  ))).__next__()
    if edge["path"] == "crossing":
        deri["Resource"][start_node["id"]]["interactions"]["swipe-right"]=end_node["id"]
        deri["Resource"][end_node["id"]]["interactions"]["swipe-left"]=start_node["id"]
    else:
        deri["Resource"][start_node["id"]]["interactions"]["swipe-up"]=end_node["id"]
        deri["Resource"][end_node["id"]]["interactions"]["swipe-down"]=start_node["id"]
        
# Create layer
deri["layers"]= {}
for layer in layers:
    deri["layers"][layer]={
        "label":layer,
        "areas":layers[layer]
    }
    
# Writing JSON
with open(os.path.join(path,"deri.json"), "w") as deri_file:
    deri_file.write(json.dumps(deri, indent=2))