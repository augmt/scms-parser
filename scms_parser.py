"""scms_parser.py parses Smogon's Content Management System's (SCMS) dex
analyses and writes JavaScript objects into .js files for use in Honko's Gen 6
Damage Calculator."""

import os
import collections
import re

def parse_scms(directory):
    """Parses the SCMS directory's .txt files and returns a dict named setdex
    with data pertaining to every Pokemon (except Ditto) with an analysis."""
    setdex = collections.defaultdict(list)
    for subdir, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(subdir, filename)
            with open(filepath, "r") as analysis:
                tier = subdir[len(directory)+1:]
                pokemon = name_pokemon(filename)
                gen = subdir[subdir.rfind("/")-2:subdir.rfind("/")]
                if tier != "VGC12" and tier != "VGC11" and pokemon != "Ditto":
                    while True:
                        line = analysis.readline()
                        if not line:
                            break
                        if line.strip()[0:4] == "name":
                            line = line.strip()
                            if tier == "Unreleased":
                                if pokemon == "Groudon" or pokemon == "Kyogre":
                                    pokemon = pokemon + "-Primal"
                                set_name = line[line.find("["):]
                            else:
                                set_name = tier + " " + line[line.find(" ")+1:]
                            set_details = get_set_details(tier, analysis, gen)
                            if do_not_append(set_details, set_name, gen):
                                continue
                            setdex[pokemon].append({set_name:set_details})
    return collections.OrderedDict(sorted(setdex.items()))

def name_pokemon(filename):
    """Returns a Pokemon's name based upon their analysis' filename and their
    current/only forme."""
    if filename.find(".old") > -1:
        pokemon = filename[:filename.find(".old")]
    else:
        pokemon = filename[:filename.find(".txt")]
        if pokemon == "Pumpkaboo" or pokemon == "Gourgeist":
            pokemon = pokemon + "-Average"
        elif pokemon == "Meowstic-M":
            pokemon = "Meowstic"

    if "-" not in pokemon:
        return pokemon

    base_forme = pokemon[:pokemon.find("-")] if pokemon.find("-") > -1 else pokemon
    excepted_base_formes = ["Arceus", "Porygon", "Gourgeist", "Nidoran", "Meowstic", "Pumpkaboo"]
    if base_forme not in excepted_base_formes and pokemon != "Ho-Oh":
        if (base_forme != "Wormadam" and pokemon != "Rotom-Mow" and
                pokemon != "Rotom-Fan"):
            pokemon = pokemon[:pokemon.find("-")+2]
        elif pokemon == "Wormadam-Sandy":
            pokemon = "Wormadam-G"
        elif pokemon == "Wormadam-Trash":
            pokemon = "Wormadam-S"
        elif pokemon == "Rotom-Mow":
            pokemon = "Rotom-C"
        else:
            pokemon = "Rotom-S"
    return pokemon

def get_set_details(tier, analysis, gen):
    """Traverses through an analysis file object from its current position and
    returns a dict with pertinent details about a Pokemon."""
    set_details = {}

    if tier != "LC" and tier[0:3] != "VGC":
        set_details["level"] = 100
    elif tier == "LC":
        set_details["level"] = 5
    else:
        set_details["level"] = 50

    line = analysis.readline().strip()
    while line != "":
        line = fixline(line)

        key = line[:line.find(":")].strip().lower()

        if key[0:4] == "move":
            set_details["moves"] = get_moveset(line, analysis, gen)
        elif key == "item" or key == "nature" or key == "ability":
            if line.find("/") == -1:
                set_details[key] = line[line.find(" ")+1:]
            else:
                set_details[key] = line[line.find(" ")+1:line.find("/")-1]
            if gen == "xy" and set_details[key] == "Lightningrod":
                set_details[key] = "Lightning Rod"
            if (set_details[key] == "Red Orb" or
                    set_details[key] == "Blue Orb" or set_details[key] == "Primordial Sea"):
                del set_details[key]
        elif key == "evs" or key == "ivs":
            rename_stat = {
              "hp": "hp",
              "atk": "at",
              "def": "df",
              "spa": "sa",
              "spd": "sd",
              "spe": "sp",
              "spatk": "sa",
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
                set_details[key] = stats
            else:
                stat = rename_stat[line[line.rfind(" ")+1:].lower()]
                value = line[line.find(":")+2:line.rfind(" ")]
                set_details[key] = {stat:value}
        line = analysis.readline().strip()
    return set_details

def fixline(line):
    """Replaces specific, erred lines with parser-friendly lines."""
    pattern = re.compile("(\w{1,})( \/|\/ )(\w{1,})")
    if pattern.search(line):
        line = pattern.sub("\\1 / \\3", line)
    elif line.find(" :") > -1: # BW Various & XY LC Vullaby
        line = line.replace(" :", ":")
    elif line.find("evss") > -1 or line.find("items") > -1: # XY UU Kyurem
        line = line.replace("s:", ":")
    elif line == "ivs: HP 0": # DP LC Riolu
        line = "ivs: 0 HP"
    elif line == "item:": # XY Doubles Tornadus
        line = ""
    elif line.find(" or ") > -1: # XY LC Froakie
        line = line[:line.find(" or ")]
    elif line == "4 HP IVs": # XY LC Vulpix
        line = "ivs: 4 HP"
    return line

def get_moveset(line, analysis, gen):
    """Parses an analysis file object from its current level and returns a
    Pokemon's set of moves."""
    moveset = []
    rename_move = {
      "Ancient Power": "AncientPower",
      "Dynamic Punch": "DynamicPunch",
      "Extreme Speed": "ExtremeSpeed",
      "Feint Attack": "Faint Attack",
      "High Jump Kick": "Hi Jump Kick",
      "Self-Destruct": "Selfdestruct",
      "Solar Beam": "SolarBeam",
      "Thunder Punch": "ThunderPunch"
    }

    for i in range (0, 4):
        if line.lower().find("move") > -1:
            if line.find("/") == -1:
                if line[line.find(" ")+4:] != "":
                    move = line[line.find(" ")+4:]
                else:
                    move = "null"
            else:
                move = line[line.find(" ")+4:line.find("/")-1]
            if gen != "xy" and move in rename_move:
                move = rename_move[move]
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

def do_not_append(set_details, set_name, gen):
    """Returns True if the set_name belongs to a FEAR set (if the set_name
    contains the string "Level" or "Lv."), or no nature is specified in the
    set_details dict."""
    return ((set_name.find("Level") > -1 or set_name.find("Lv.") > -1) or
            ("nature" not in set_details and gen != "gs" and gen != "rb"))

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

            # add set_name to stream
            stream += "\"" + s.keys()[0].replace("\"", "\\u0022") + "\":{"
            stream += parse_set_details(s.values()[0])
            stream += "]}"
    return stream

def parse_set_details(set_details):
    """Parses the set_details dict and returns pertinent details about a
    Pokemon within a precisely ordered string."""
    string = "\"level\":" + str(set_details['level'])
    if "evs" in set_details:
        string += ",\"evs\":{"
        for index, stat in enumerate(set_details['evs']):
            string += "\"" + stat + "\":" + set_details['evs'][stat]
            if index != len(set_details['evs']) - 1:
                string += ","
        string += "}"
    if "ivs" in set_details:
        string += ",\"ivs\":{"
        for index, stat in enumerate(set_details['ivs']):
            string += "\"" + stat + "\":" + set_details['ivs'][stat]
            if index != len(set_details['ivs']) - 1:
                string += ","
        string += "}"
    if "nature" in set_details:
        string += ",\"nature\":\"" + set_details['nature'] + "\""
    if "ability" in set_details:
        string += ",\"ability\":\"" + set_details['ability'] + "\""
    if "item" in set_details:
        string += ",\"item\":\"" + set_details['item'] + "\""
    string += ",\"moves\":[\""
    for index, move in enumerate(set_details['moves']):
        string += move + "\""
        if index != 3:
            string += ",\""
    return string

def write_js_objects():
    """Writes an object into as many JavaScript files as there are elements in
    the object_name list."""
    object_name = [
        "SETDEX_BW", "SETDEX_DPP", "SETDEX_GSC",
        "SETDEX_RBY", "SETDEX_ADV", "SETDEX_XY"
        ]
    filename = [name.lower().replace("adv", "rse") for name in object_name]
    subdirs = sorted(os.walk("dex/analyses").next()[1])
    for index, gen in enumerate(subdirs):
        setdex = parse_scms("dex/analyses/" + gen)
        with open (filename[index] + ".js", "w") as js_file:
            js_file.write("var " + object_name[index] + "={" + parse_setdex(setdex) + "}};")

if __name__ == '__main__':
    write_js_objects()
