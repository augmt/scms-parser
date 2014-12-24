"""poke-parser.py parses Smogon's Content Management System's (SCMS) dex
analyses and writes JavaScript objects into .js files for use in Honko's Gen 6
Damage Calculator."""

import os
import collections
import re
import copy

def parse_scms(directory):
    """Parses an SCMS directory's txt files and returns a dict, setdex, with
    data pertaining to every Pokemon (except Ditto) with an analysis."""
    setdex = collections.defaultdict(list)
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(subdir, file)
            with open(filepath, "r") as analysis:
              tier = subdir[len(directory)+1:]
              pokemon = name_pokemon(file)
              gen = subdir[subdir.rfind("/")-2:subdir.rfind("/")]
              if tier != "VGC12" and tier != "VGC11" and pokemon != "Ditto":
                  while True:
                      line = analysis.readline()
                      if not line:
                          break
                      if line.strip()[0:4] == "name":
                          line = line.strip()
                          if tier == "Unreleased":
                              set_name = line[line.find("["):]
                          else:
                              set_name = tier + " " + line[line.find(" ")+1:]
                          if set_name.find("Level") > -1 or set_name.find("Lv.") > -1: # skip over FEAR sets
                              continue
                          set_details = get_set_details(tier, analysis)
                          if ("nature" not in set_details and gen != "gs" and gen != "rb"):
                              continue
                          if "Relic Song" in set_details["moves"]:
                              setdex[pokemon+"-P"].append({set_name:set_details})
                          if pokemon == "Aegislash":
                              setdex[pokemon+"-Shield"].append({set_name:set_details})
                              setdex[pokemon+"-Blade"].append({set_name:set_details})
                              continue
                          if has_megastone(set_details):
                              append_mega_evolution(set_details, pokemon, set_name, setdex)
                          setdex[pokemon].append({set_name:set_details})
    return setdex

def name_pokemon(file):
    """Returns a Pokemon's name based upon their analysis' filename and their 
    current/only forme."""
    if file.find(".old") > -1:
        pokemon = file[:file.find(".old")]
    else:
        pokemon = file[:file.find(".txt")]

    if "-" not in pokemon and pokemon != "Gourgeist":
        return pokemon

    base_forme = pokemon[:pokemon.find("-")] if pokemon.find("-") > -1 else pokemon
    uniform_pokemon = ["Arceus", "Porygon", "Gourgeist", "Nidoran", "Meowstic"]
    if base_forme not in uniform_pokemon and pokemon != "Ho-Oh":
        if (base_forme != "Wormadam" and pokemon != "Rotom-Mow" and
                pokemon != "Rotom-Fan"):
            return pokemon[:pokemon.find("-")+2]
        elif pokemon == "Wormadam-Sandy":
            return "Wormadam-G"
        elif pokemon == "Wormadam-Trash":
            return "Wormadam-S"
        elif pokemon == "Rotom-Mow":
            return "Rotom-C"
        else:
            return "Rotom-S"
    elif pokemon == "Gourgeist":
        return pokemon + "-Average"
    return pokemon

def get_set_details(tier, analysis):
    """Traverses through an analysis file object from its current position and
    returns a dict with pertinent details about a Pokemon."""
    sdet = {}

    if tier != "LC" and tier[0:3] != "VGC":
        sdet["level"] = 100
    elif tier == "LC":
        sdet["level"] = 5
    else:
        sdet["level"] = 50

    line = analysis.readline().strip()
    while line != "":
        line = fixline(line)

        key = line[:line.find(":")].strip().lower()

        if key[0:4] == "move":
            sdet["moves"] = get_moveset(line, analysis)
        elif key == "item" or key == "nature" or key == "ability":
            if line.find("/") == -1:
                sdet[key] = line[line.find(" ")+1:]
            else:
                sdet[key] = line[line.find(" ")+1:line.find("/")-1]
        elif key == "evs" or key == "ivs":
            rename_stat = {
              "hp": "hp",
              "atk": "at",
              "def": "df",
              "spa": "sa",
              "spd": "sd",
              "spe": "sp",
              "spdef": "sd",
              "speed": "sp"
            }
            if line.find("/") > -1:
                stats = {}
                while line.find("/") > -1:
                    svp = line[line.find(" ")+1:line.find("/")].strip() # stat-value pair
                    stat = rename_stat[svp[svp.find(" ")+1:].lower()]
                    stats[stat] = svp[:svp.find(" ")]
                    line = line[line.find("/")+1:]
                svp = line.strip()
                stat = rename_stat[svp[svp.find(" ")+1:].lower()]
                stats[stat] = svp[:svp.find(" ")]
                sdet[key] = stats
            else:
                stat = rename_stat[line[line.rfind(" ")+1:].lower()]
                value = line[line.find(":")+2:line.rfind(" ")]
                sdet[key] = {stat:value}
        line = analysis.readline().strip()
    return sdet

def fixline(line):
    """Replaces specific, erred lines with parser-friendly lines. Does not
    alter file contents."""
    pattern = re.compile("(\w{1,})( \/|\/ )(\w{1,})")
    if pattern.search(line):
        return pattern.sub("\\1 / \\3", line)
    if line.find(" :") > -1: # BW Various & XY LC Vullaby
        return line.replace(" :", ":")
    if line.find("evss") > -1 or line.find("items") > -1: # XY UU Kyurem & Unreleased Swampert
        return line.replace("s:", ":")
    if line == "ivs: HP 0": # DP LC Riolu
        return "ivs: 0 HP"
    if line.find(" or ") > -1: # XY LC Froakie
        return line[:line.find(" or ")]
    if line == "4 HP IVs": # XY LC Vulpix
        return "ivs: 4 HP"
    return line

def get_moveset(line, analysis):
    """Parses an analysis file object from its current level and returns a
    Pokemon's set of moves."""
    moveset = []

    for i in range (0, 4):
        if line.lower().find("move") > -1:
            if line.find("/") == -1:
                if line[line.find(" ")+4:] != "":
                    move = line[line.find(" ")+4:]
                else:
                    move = "null"
            else:
                move = line[line.find(" ")+4:line.find("/")-1]
        else:
            for _ in range (i, 4):
                moveset.append("null")
            analysis.seek(previous_line)
            return moveset
        moveset.append(move)

        if i < 3:
            previous_line = analysis.tell()
            line = analysis.readline().strip()

    return moveset

def has_megastone(sdet):
    """Checks a Pokemon's set's details and returns a bool as to whether the set
    includes a Mega Stone or not."""
    if "item" in sdet and ("ite" in sdet["item"] or sdet["item"] == "Blue Orb" or
            "Dragon Ascent" in sdet["moves"] or sdet["item"] == "Red Orb"):
        if sdet["item"] != "Eviolite" and sdet["item"] != "White Herb":
            return True
    return False

def append_mega_evolution(sdet, pokemon, set_name, setdex):
    """Appends a Pokemon's Mega Evolution or Primal Reversion to the setdex."""
    mega_pokemon = "Mega " + pokemon
    mega_sdet = copy.deepcopy(sdet)
    if "ability" in mega_sdet:
        del mega_sdet["ability"]
    if pokemon != "Rayquaza":
        del mega_sdet["item"]
    if sdet["item"][-2:] == " X" or sdet["item"][-2:] == " Y":
        mega_pokemon = "Mega " + pokemon + sdet["item"][-2:]
    if sdet["item"] == "Blue Orb" or sdet["item"] == "Red Orb":
        mega_pokemon = "Primal " + pokemon
    setdex[mega_pokemon].append({set_name:mega_sdet})

def parse_setdex(setdex):
    """Parses the setdex dict and returns a string which is used to write a .js
    file for use in Honko's calculator."""
    stream = ""
    for (pokemon, sets) in setdex.iteritems():
        if stream != "": 
            stream += "},"
        stream += "\"" + pokemon.replace("\'", "\\u0027") + "\":{"

        for s in sets:
            if s != sets[0]: 
                stream += ","
            set_details = s.values()[0]
            stream += "\"" + s.keys()[0].replace("\"", "\\u0022") + "\":{"

            stream += "\"level\":" + str(set_details['level'])
            if "evs" in set_details:
                stream += ",\"evs\":{"
                for index, stat in enumerate(set_details['evs']):
                    stream += "\"" + stat + "\":" + set_details['evs'][stat]
                    if index != len(set_details['evs']) - 1:
                        stream += ","
                stream += "}"
            if "ivs" in set_details:
                stream += ",\"ivs\":{"
                for index, stat in enumerate(set_details['ivs']):
                    stream += "\"" + stat + "\":" + set_details['ivs'][stat]
                    if index != len(set_details['ivs']) - 1:
                        stream += ","
                stream += "}"
            if "nature" in set_details:
                stream += ",\"nature\":\"" + set_details['nature'] + "\""
            if "ability" in set_details:
                stream += ",\"ability\":\"" + set_details['ability'] + "\""
            if "item" in set_details:
                stream += ",\"item\":\"" + set_details['item'] + "\""
            stream += ",\"moves\":[\""
            for index, move in enumerate(set_details['moves']):
                stream += move + "\""
                if index != 3:
                    stream += ",\""
            stream += "]}"
    return stream

if __name__ == '__main__':
    SETDEX_RBY = parse_scms("scms/dex/analyses/rb")
    with open("setdex_rby.js", "w") as rbfile:
        rbfile.write("var SETDEX_RBY={" + parse_setdex(SETDEX_RBY) + "}};")

    SETDEX_GSC = parse_scms("scms/dex/analyses/gs")
    with open("setdex_gsc.js", "w") as gsfile:
        gsfile.write("var SETDEX_GSC={" + parse_setdex(SETDEX_GSC) + "}};")

    SETDEX_RSE = parse_scms("scms/dex/analyses/rs")
    with open("setdex_rse.js", "w") as rsfile:
        rsfile.write("var SETDEX_ADV={" + parse_setdex(SETDEX_RSE) + "}};")

    SETDEX_DPP = parse_scms("scms/dex/analyses/dp")
    with open("setdex_dpp.js", "w") as dpfile:
        dpfile.write("var SETDEX_DPP={" + parse_setdex(SETDEX_DPP) + "}};")

    SETDEX_BW = parse_scms("scms/dex/analyses/bw")
    with open("setdex_bw.js", "w") as bwfile:
        bwfile.write("var SETDEX_BW={" + parse_setdex(SETDEX_BW) + "}};")

    SETDEX_XY = parse_scms("scms/dex/analyses/xy")
    with open("setdex_xy.js", "w") as xyfile:
        xyfile.write("var SETDEX_XY={" + parse_setdex(SETDEX_XY) + "}};")
