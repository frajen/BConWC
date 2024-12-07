import traceback
from utils import (hex2int, write_multi, read_multi, ITEM_TABLE,
                   CUSTOM_ITEMS_TABLE, mutate_index,
                   name_to_bytes, utilrandom as random,
                   Substitution)
from utils import TEXT_TABLE
from skillrandomizer import get_ranked_spells, get_spell
from options import Options_

# future blocks: chests, morphs, shops



########WC - add section to handle item descriptions
texttable = {}
f = open(TEXT_TABLE)
for line in f:
    line = line.strip()
    char, value = tuple(line.split())
    #texttable[char] = value     <- reverse the table for lookup purposes
    texttable[value] = char
#texttable[' '] = 'FE'   <- reverse the table for lookup purposes
texttable['FE'] = ' '
texttable['fe'] = ' '
texttable['ff'] = ' '
texttable['1'] = '<line>'
texttable['0'] = '<end>'
texttable['d3'] = '"' #open quote, actually
texttable['c6'] = ','
texttable['c7'] = '...'
texttable['cd'] = '%'
texttable['d8'] = '<dirk icon>'
texttable['d9'] = '<sword icon>'
texttable['da'] = '<lance icon>'
texttable['db'] = '<knife icon>'
texttable['dc'] = '<rod icon>'
texttable['dd'] = '<brush icon>'
texttable['de'] = '<stars icon>'
texttable['df'] = '<special icon>'
texttable['e0'] = '<gambler icon>'
texttable['e1'] = '<claw icon>'
texttable['e2'] = '<shield icon>'
texttable['e3'] = '<helmet icon>'
texttable['e4'] = '<armor icon>'
texttable['e5'] = '<tool icon>'
texttable['e6'] = '<skean icon>'
texttable['e7'] = '<relic icon>'

f.close()
########WC - add section to handle item descriptions


ITEM_STATS = ["learnrate", "learnspell", "fieldeffect",
              "statusprotect1", "statusprotect2", "statusacquire3",
              "statboost1", "special1", "statboost2", "special2",
              "special3", "targeting", "elements", "speedvigor",
              "magstam", "breakeffect", "otherproperties", "power",
              "hitmdef", "elemabsorbs", "elemnulls", "elemweaks",
              "statusacquire2", "mblockevade", "specialaction"]

STATPROTECT = {"fieldeffect": 0xdc,
               "statusprotect1": 0x00,
               "statusprotect2": 0x00,
               "statusacquire3": 0x00,
               "statboost1": 0x00,
               "special1": 0x00,
               "statboost2": 0x02,
               "special2": 0x28,
               "special3": 0x60,
               "otherproperties": 0xdf,
               "statusacquire2": 0x00}

all_spells = None
effects_used = []
effects_used = []
itemdict = {}
customs = {}
changed_commands = []

break_unused_dict = {0x09: list(range(0xA3, 0xAB)),
                     0x08: list(range(0xAB, 0xB0)) + list(range(0x41, 0x44))}


def set_item_changed_commands(commands):
    global changed_commands
    changed_commands = set(commands)


def get_custom_items():
    if customs:
        return customs

    customname, customdict = None, None
    for line in open(CUSTOM_ITEMS_TABLE):
        while '  ' in line:
            line = line.replace('  ', ' ')
        line = line.strip()
        if not line or line[0] == '#':
            continue

        if line[0] == '!':
            if customname is not None:
                customs[customname] = customdict
            customdict = {}
            customname = line[1:].strip()
            continue

        key, value = tuple(line.split(' ', 1))
        customdict[key] = value

    customs[customname] = customdict
    return get_custom_items()


def bit_mutate(byte, op="on", nochange=0x00):
    if op == "on":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        byte = byte | bit
    elif op == "off":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        bit = 0xff ^ bit
        byte = byte & bit
    elif op == "invert":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        byte = byte ^ bit
    return byte


def extend_item_breaks(fout):
    #https://github.com/seibaby/ff3us/blob/master/ff6_bank_c2_battle.asm
    #C22735:  LDA $D85012,X  ;equipment spell byte.
    #; Bits 0-5: spell 
    #; Bit 6: cast randomly after weapon strike [handled
    #;        elsewhere, shouldn't apply here]
    #; Bit 7: 1 = remove from inventory upon usage, 0 = nope
    #SEP #$10       ;Set 8-bit X and Y
    #RTS
    break_sub = Substitution()
    break_sub.set_location(0x22735)
    break_sub.bytestring = bytes([0x22, 0x13, 0x30, 0xF0])
    break_sub.write(fout)

    #C2273C:  CMP #$E6       ;Carry is set if item # >= 230, Sprint Shoes.  i.e. it's
    #               ;Item type.  Carry won't be set for Equipment Magic.
    #JSR C2271A     ;get Targeting byte, and make slight modification to
    #               ;targeting if Item affects Wound/Zombie/Petrify.  also,
    #               ;A = equipment spell byte
    #BCS C22707     ;if it's a plain ol' Item, always deduct from inventory,
    #               ;and don't attempt to save the [meaningless] spell # or
    #               ;load spell data
    #BMI C2274B     ;branch if equipment gets used up when used for Item Magic.
    #               ;i'm not aware of any equipment this *doesn't* happen with,
    #               ;though the game supports it.
    #XBA            ;preserve equipment spell byte
    #LDA #$10
    #TSB $B1        ;set "don't deplete from Item inventory" flag
    #XBA
    break_sub.set_location(0x22743)
    break_sub.bytestring = bytes([0x30, 0x05])
    break_sub.write(fout)

    break_sub.set_location(0x2274A)
    break_sub.bytestring = bytes([0xAD, 0x10, 0x34])
    break_sub.write(fout)

    #C229CE:  LDA $3B68,X
    break_sub.set_location(0x229ED)
    break_sub.bytestring = bytes([0x22, 0x00, 0x30, 0xF0, 0xEA, 0xEA])
    break_sub.write(fout)

    #C23649:  LDA $3A89
    break_sub.set_location(0x23658)
    break_sub.bytestring = bytes([0xAD, 0x7E, 0x3A])
    break_sub.write(fout)

    #writing to F0 3000, shared space with WC?
    break_sub.set_location(0x303000)
    break_sub.bytestring = bytes(
        [0xBD, 0xA4, 0x3B, 0x29, 0x0C, 0x0A, 0x0A, 0x0A, 0x0A, 0x8D, 0x89, 0x3A, 0xBD, 0x34, 0x3D, 0x8D, 0x7E, 0x3A,
         0x6B, 0x08, 0xBF, 0x12, 0x50, 0xD8, 0x8D, 0x10, 0x34, 0xBF, 0x13, 0x50, 0xD8, 0x0A, 0x0A, 0x0A, 0x0A, 0x28,
         0x29, 0xC0, 0x6B])
    break_sub.write(fout)

#items from tables/itemcodes.txt
#Begins with:
#0,185000,Dirk
#185000 is the beginning of Item Data in ROM
    
class ItemBlock:
    def __init__(self, itemid, pointer, name):
        self.itemid = hex2int(itemid)
        self.pointer = hex2int(pointer)
        self.name = name
        self.degree = None
        self.banned = False
        self.itemtype = 0

        self.price = 0
        self._rank = None
        self.dataname = bytes()
        self.heavy = False

        self.mutation_log = {}

        #WC - add modded name, icon
        self.read_in_name = ""
        self.itemicon = ""

    @property
    def is_tool(self):
        return self.itemtype & 0x0f == 0x00

    @property
    def is_weapon(self):
        return self.itemtype & 0x0f == 0x01

    @property
    def is_armor(self):
        return self.is_body_armor or self.is_shield or self.is_helm

    @property
    def is_body_armor(self):
        return self.itemtype & 0x0f == 0x02

    @property
    def is_shield(self):
        return self.itemtype & 0x0f == 0x03

    @property
    def is_helm(self):
        return self.itemtype & 0x0f == 0x04

    @property
    def is_relic(self):
        return self.itemtype & 0x0f == 0x05

    @property
    def is_consumable(self):
        return self.itemtype & 0x0f == 0x06

    def set_degree(self, value):
        self.degree = value

    def read_stats(self, filename):
        global all_spells

        f = open(filename, 'r+b')
        f.seek(self.pointer)
        self.itemtype = ord(f.read(1))

        # throwable = self.itemtype & 0x10
        # usable_battle = self.itemtype & 0x20
        # usable_field = self.itemtype & 0x40

        self.equippable = read_multi(f, length=2)
        self.heavy = bool(self.equippable & 0x8000)

        stats = list(f.read(len(ITEM_STATS)))
        self.features = dict(list(zip(ITEM_STATS, stats)))

        # move flags for "randomly cast" and "destroy if used"
        # so breakeffect can use the full range of spells
        if not self.is_consumable:
            #print(self.name)
            #print(self.features["breakeffect"])
            #print(self.features["otherproperties"])

            pass

            ######WC - leave this alone until use of F0 bank is understood
            #break_flags = self.features["breakeffect"] & 0xC0
            #self.features["otherproperties"] |= break_flags >> 4
            #self.features["breakeffect"] &= ~0xC0

            #print(self.features["breakeffect"])
            #print(self.features["otherproperties"])
        self.price = read_multi(f, length=2)

        if all_spells is None:
            all_spells = get_ranked_spells(filename)
            all_spells = [s for s in all_spells if s.valid]

        ###WC - add section to grab names if they have been changed
        f.seek(0x12B300 + (13 * self.itemid))
        iconcheck = 0
        name_str = ""
        itemnamelist = list(f.read(13))
        for x in itemnamelist:
            if iconcheck == 0:
                name_hexval = str(hex(x))
                self.itemicon = texttable[name_hexval[2:]]
                iconcheck = 1
            else:
                name_hexval = str(hex(x))
                name_str = name_str + texttable[name_hexval[2:]]
        self.read_in_name = name_str.strip()
        ###WC - add section to grab names if they have been changed        

        f.seek(0x2CE408 + (8 * self.itemid))
        self.weapon_animation = list(f.read(8))

        f.seek(0x12B300 + (13 * self.itemid))
        self.dataname = list(f.read(13))

        ###WC - grab the description
        f.seek(0x2D7AA0 + (2* self.itemid))
        descpointer = read_multi(f, length=2)  #get the pointer offset
        if 0 == 1:
            print(self.name)
            print("offset: " + str(descpointer))
            desc_vals = []
            descstart = f.seek(0x2D6400 + descpointer) #get to the actual desc 
            desc_val = 1
            desc_str = ""
            while desc_val != 0:
                desc_val = ord(f.read(1))
                desc_vals.append(desc_val)
                desc_hexval = str(hex(desc_val))
                desc_str = desc_str + texttable[desc_hexval[2:]]
            print(desc_vals)
            print(desc_str)
        ###WC - grab the description

        #print(texttable['80'])
        #hexme = str(hex(desc_vals[0]))
        #hexme = hexme[2:]
        #print(str(hexme))
        #input("X")

        # unhardcoded tintinabar patch moves the tintinabar flag
        #if self.features["fieldeffect"] & 0x80:
            #self.features["fieldeffect"] &= ~0x80
            #self.features["special2"] |= 0x80

        f.close()

    def ban(self):
        self.banned = True

    def become_another(self, customdict=None, tier=None):
        customs = get_custom_items()
        if customdict is None:
            if tier is None:
                candidates = [customs[key] for key in sorted(customs)]
            else:
                candidates = [customs[key] for key in sorted(customs) if customs[key]["tier"] == tier]
            customdict = random.choice(candidates)

        for key in self.features:
            self.features[key] = 0

        def convert_value(v):
            v = v.split()

            def intify(value):
                subintify = lambda x: int(x, 0x10)
                if ',' in value:
                    return random.choice(list(map(subintify, value.split(','))))
                return subintify(value)

            if len(v) == 1:
                return intify(v[0])
            return list(map(intify, v))

        name = bytes()
        for key, value in customdict.items():
            if key == "name_text":
                name = name + name_to_bytes(value, 12)
            elif key == "description":
                pass
            elif key == "tier":
                pass
            else:
                value = convert_value(value)
                if key == "name_icon":
                    name = bytes([value]) + name
                elif hasattr(self, key):
                    setattr(self, key, value)
                elif key in self.features:
                    self.features[key] = value

        self.dataname = name
        self.ban()

    def write_stats(self, fout):
        fout.seek(self.pointer)
        fout.write(bytes([self.itemtype]))

        self.confirm_heavy()
        write_multi(fout, self.equippable, length=2)

        s = bytes([self.features[key] for key in ITEM_STATS])
        fout.write(s)

        write_multi(fout, self.price, length=2)

        #ECE400 to ECE6E7 Weapon Animation Data (93 items, 8 bytes each)
        #C00000 + 2CE408 = ECE408
        if self.is_weapon or (self.itemtype & 0x0f) == 0x01:
            #itemid 93 = 5D in hex, listed as Gold Shld in itemcodes.txt
            #the last item seems to be Tiger Fangs?
            #59,185a6e,Tiger Fangs
            #5a,185a8c,Buckler
            #5b,185aaa,Heavy Shld
            #5c,185ac8,Mithril Shld
            #5d,185ae6,Gold Shld
            if self.itemid < 93:
                #print("before 93: " + self.name + " | " + self.id)
                fout.seek(0x2CE408 + (8 * self.itemid))
            else:
                print("93 and up: " + self.name)
                #if the itemid is 93+ then go to F031000
                fout.seek(0x303100 + (8 * (self.itemid - 93)))
            fout.write(bytes(self.weapon_animation))

        #D2B300 Item Names
        fout.seek(0x12B300 + (13 * self.itemid))
        fout.write(bytes(self.dataname))

    def confirm_heavy(self):
        if self.heavy and self.equippable:
            self.equippable |= 0x8000
        else:
            self.equippable &= 0x7FFF

    def equippable_by(self, charid):
        return self.equippable & (1 << charid)

    def unrestrict(self):
        if self.is_weapon:
            self.itemtype |= 0x10
            self.features['otherproperties'] |= 0x82

    @property
    def has_disabling_status(self):
        if self.features['statusacquire2'] & 0xf9:
            return True
        if self.features['statusacquire3'] & 0x14:
            return True
        return False

    @property
    def imp_only(self):
        return self.equippable & 0x4000

    @property
    def prevent_encounters(self):
        return bool(self.features['fieldeffect'] & 0x02)

    @property
    def evade(self):
        mblockevade = self.features['mblockevade']
        evade = mblockevade & 0x0f
        return evade

    @property
    def mblock(self):
        mblockevade = self.features['mblockevade']
        mblock = (mblockevade & 0xf0) >> 4
        return mblock

    def get_mutation_log(self):
        if not self.mutation_log:
            return None
        s = self.name + ": \n"
        for k, v in self.mutation_log.items():
            s += f"    {k}: {v}\n"
        return s


    def pick_a_spell(self, magic_only=False, custom=None):
        if magic_only:
            #spells = [s for s in all_spells if s.spellid in range(0, 36)]
            spells = [s for s in all_spells if s.spellid in range(0, 36) and s.spellid != 20]
        else:
            spells = all_spells

        if custom:
            spells = list(filter(custom, spells))

        spells = sorted(spells, key=lambda s: s.rank())
        items = get_ranked_items()
        index = items.index(self)
        index = int((index / float(len(items))) * len(spells))
        index = mutate_index(index, len(spells), [False, True, True],
                             (-5, 4), (-3, 3))
        spell = spells[index]

        return spell, index / float(len(spells))

    def get_feature(self, feature, feature_byte, nochange):

        features = {
            "statboost1": {e: 1 << i for i, e in
                      enumerate(["Bat. Pwr +1/4", "Mag. Pwr +1/2", "+1/4 HP",
                      "+1/2 HP", "+1/8 HP", "+1/4 MP", "+1/2 MP", "+1/8 MP"])},
            "statboost2": {e: 1 << i for i, e in
                      enumerate(["Better Steal", "Mag. Pwr +1/4",
                      "Better Sketch","Better Control", "100% Hit Rate",
                      "1/2 MP Cost", "MP cost = 1", "Vigor +50%"])},
            "special1": {e: 1 << i for i, e in
                      enumerate(["Initiative", "Vigilance", "Command Changer",
                      "Command Changer", "Command Changer", "Command Changer",
                      "Command Changer", "Super Jump"])},
            "special2": {e: 1 << i for i, e in
                      enumerate(["Fight -> X-Fight", "Can counter",
                      "Random Evade", "Use weapon 2-handed",
                      "Can equip 2 weapons", "Can equip anything",
                      "Cover", "Step regen"])},
            "special3": {e: 1 << i for i, e in
                      enumerate(["Fight -> X-Fight", "Can counter", "Random Evade",
                      "Use weapon 2-handed", "Can equip 2 weapons",
                      "Can equip anything", "Cover", "Step regen"])},
            "statusprotect1": {e: 1 << i for i, e in
                      enumerate(["No dark", "No zombie", "No poison",
                      "No magitek", "No clear", "No imp",
                      "No petrify", "Death protection"])},
            "statusprotect2": {e: 1 << i for i, e in
                      enumerate(["No condemned", "Near fatal always",
                      "No image", "No mute", "No berserk", "No muddle",
                      "No seizure", "No sleep"])},
            "statusacquire2": {e: 1 << i for i, e in
                      enumerate(["Condemned", "Near fatal", "Image", "Mute",
                      "Berserk", "Muddle", "Seizure", "Sleep"])},
            "statusacquire3": {e: 1 << i for i, e in
                      enumerate(["Auto float", "Auto regen", "Auto slow",
                      "Auto haste", "Auto stop", "Auto shell",
                      "Auto safe", "Auto reflect"])},
            "fieldeffect": {e: 1 << i for i, e in
                      enumerate(["1/2 enc.", "No enc.", "", "", "",
                      "Sprint", "", ""])},
            "otherproperties": {e: 1 << i for i, e in
                      enumerate(["", "", "Procs", "Breaks", "", "", "", ""])}
        }

        #what is "No magitek"

        try:
            FEATURE_FLAGS = features[feature]
        except KeyError:
            FEATURE_FLAGS = None

        # Comparing (v & feature_byte) to (v & nochange) appears to detect if the feature is a vanilla feature.
        # TODO: Adjust the string composition below so that procs and breaks can be handled differently.
        #  Procs and breaks need to check the spell used to determine if they are different than vanilla,
        #  otherwise items that break and proc in vanilla will not show up in the log even if they proc/break
        #  a different spell than in vanilla.
        if FEATURE_FLAGS:
            s = ", ".join([e for e, v in FEATURE_FLAGS.items() if v & feature_byte == v and v & feature_byte != v & nochange])

        # Note that this doesn't catch an error if s is not defined.
        return s

    def mutate_feature(self, feature=None):
        if self.is_consumable or self.is_tool:
            return

        if feature is None:
            feature = random.choice(list(STATPROTECT.keys()))

        #print(feature)

        nochange = STATPROTECT[feature]
        if feature == 'special2':
            # Allow rare merit award bit on relics
            if self.is_relic:
                if random.randint(1, 10) == 10:
                    nochange &= ~0x20
            # Reduce chance of Genji Glove bit on non-relics
            elif random.randint(1, 4) != 4:
                nochange |= 0x10

        #chance of Command Changer
        if feature == "special1":
            #print("Before: " + str(self.features["special1"]))
            pass

        self.features[feature] = bit_mutate(self.features[feature], op="on",
                                            nochange=nochange)
        if feature == "special1":
            #print("After: " + str(self.features["special1"]))
            pass

        new_features = self.get_feature(feature, self.features[feature], nochange)

        if feature == "special1":
            #print("New Feature: " + str(new_features))
            if self.features["special1"] == 4 or self.features["special1"] == 8 or \
            self.features["special1"] == 16 or self.features["special1"] == 32 or \
            self.features["special1"] == 64:
                #print(self.name)  # <-- only print if Item got Command Change feature
                pass

        if new_features != "":
            if "Special Feature" in self.mutation_log.keys():
                for new_feature in new_features.split(", "):
                    if new_feature not in self.mutation_log["Special Feature"]:
                        self.mutation_log.update({"Special Feature": self.mutation_log["Special Feature"] + ", " + new_feature})
            else:
                self.mutation_log["Special Feature"] = new_features
        self.mutate_name()


    def mutate_break_effect(self, always_break=False, wild_breaks=False, no_breaks=False, unbreakable=False):
        global effects_used
        if self.is_consumable:
            return

        if no_breaks:
            self.itemtype &= ~0x20
            return

        if unbreakable:
            self.features['otherproperties'] &= ~0x08
            return

        if always_break:
            effects_used = []

        ###WC - leave vanilla spell procs/breaks alone?
        if self.features['breakeffect'] != 0:
            #print(self.name + str(self.features['breakeffect']))
            return

        success = False
        ####turn off for WC
        #max_spellid = 0xFE if wild_breaks else 0x50

        #limit to range available in D85012
        #max_spellid = 0x3F

        #limit to spells+Esper summons+ magic throws+storm
        max_spellid = 0x54

        #limit to spells
        #max_spellid = 0x36
        spell_disallow = [21, 22, 23, 24, 28, 31, 34, 36, 37, 39, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53,
                          71, 72, 73, 74, 75, 76, 77, 78, 79, 80]
        #limit to spells+Esper summons
        #max_spellid = 0x50
        for _ in range(100):
            spell, _ = self.pick_a_spell(custom=lambda x: x.spellid <= max_spellid)
            #if spell.spellid not in effects_used:

            #WC - add in a banned spell list
            if spell.spellid not in effects_used and spell.spellid not in spell_disallow:
                effects_used.append(spell.spellid)
                success = True
                break

        if not success:
            return


        # swdtechs, blitzes, superball, and slots don't seem to work
        # correctly with procs, but they work with breaks.
        # (Mostly they just play the wrong animation, but a couple
        # softlock.)
        no_proc_ids = list(range(0x55, 0x66)) + list(range(0x7D, 0x82))

        #set the spell ID regardless of whether it will be usable
        self.features['breakeffect'] = spell.spellid


        #all non-weapons become usable in battle, all weapons have a
        #50% chance to set usable in battle
        #WC - turn this off for now
        # always make armors usable in battle; weapons, only sometimes
        if 0 == 1 and (not self.is_weapon or random.randint(1, 2) == 2 or always_break or spell.spellid in no_proc_ids):
            self.itemtype = self.itemtype | 0x20

        #####WC - skip this for now. BC moves the
        #####random casting bit to 0x85013 $04 (the bit after the enable swdtech bit) and
        #####break when used bit to 0x85013 $08
        ######so functionally this does nothing for WC

        #flag to break when used as an item
        #if random.randint(1, 20) == 20:
        if random.randint(1, 20) == 20 and 0 == 1:
            #5% chance that $08 is cleared if the item already is not broken when used
            #in WC this functionally does nothing
            self.features['otherproperties'] &= 0xF7
        else:
            #otherwise, 95% chance that the item breaks when used. Note that is rendered irrelevant
            #if the itemtype does not allow the item to be used in battle
            #self.features['otherproperties'] |= 0x08
            pass

        # flag to set chance to proc a spell
        #50% chance for all items, or
        #self.itemtype & 0x20 means the item is usable in battle, so don't apply this to anything that
        #already can be used in battle
        
        #WC - increase the chance of a spell proc from 50% to 70%
        #if self.is_weapon and spell.spellid not in no_proc_ids and (
                #not self.itemtype & 0x20 or random.randint(1, 2) == 2):
        if self.is_weapon and spell.spellid not in no_proc_ids and (
                not self.itemtype & 0x20 or random.randint(1, 10) >= 4):
            ###WC - no longer need to use otherproperties to mark a spell proc
            #self.features['otherproperties'] |= 0x04
            #self.mutation_log["Proc"] = get_spell(self.features['breakeffect']).name
            #print("Proc added: " + get_spell(self.features['breakeffect']).name)
            
            #instead use breakeffect's 0x40
            self.features['breakeffect'] |= 0x40
            self.mutation_log["Proc"] = get_spell(self.features['breakeffect'] ^ 0x40).name

            #print("Proc added: " + get_spell(self.features['breakeffect'] ^ 0x40).name)

            #example:
            #self.features['breakeffect'] = 66  #0x40 is allow random casting, 0x2 is bolt, 0x42 = 66 dec
            #self.features['otherproperties'] = 2  #enable swdtech
            
        else:
            #Sets the random casting bit 0x85013 $04 to 0 unless it is already 1
            #in WC this functionally does nothing
            self.features['otherproperties'] &= 0xFB


        self.features['targeting'] = spell.targeting & 0xef
        self.mutate_name()

    def get_element(self, elem_byte):
        ELEM_FLAGS = {e: 1 << i for i, e in
                      enumerate(["fire", "ice", "lightning", "poison", "wind", "pearl", "earth", "water"])}
        s = ", ".join([e for e, v in ELEM_FLAGS.items() if v & elem_byte == v])

        return s

    def mutate_elements(self):
        if self.is_consumable or self.is_tool:
            return

        def elemshuffle(elements):
            elemcount = bin(elements).count('1')
            while random.randint(1, 5) == 5:
                elemcount += random.choice([-1, 1])
            elemcount = max(0, min(elemcount, 8))
            elements = 0
            while elemcount > 0:
                elements = elements | (1 << random.randint(0, 7))
                self.mutate_name()
                elemcount += -1
            return elements


        self.features['elements'] = elemshuffle(self.features['elements'])
        if self.is_weapon:
            if self.features['elements']:
                self.mutation_log["Elemental damage"] = self.get_element(self.features['elements'])
        else:
            if self.features['elements']:
                self.mutation_log["Halves elemental damage"] = self.get_element(self.features['elements'])

        if self.is_weapon:
            return

        self.features['elemabsorbs'] = elemshuffle(self.features['elemabsorbs'])
        if self.features['elemabsorbs']:
            self.mutation_log["Absorbs elemental damage"] = self.get_element(self.features['elemabsorbs'])
        self.features['elemnulls'] = elemshuffle(self.features['elemnulls'])
        if self.features['elemnulls']:
            self.mutation_log["Nulls elemental damage"] = self.get_element(self.features['elemnulls'])
        self.features['elemweaks'] = elemshuffle(self.features['elemweaks'])
        if self.features['elemweaks']:
            self.mutation_log["Weak to elemental damage"] = self.get_element(self.features['elemweaks'])


    def mutate_learning(self):
        if not self.is_armor and not self.is_relic:
            return

        spell, rank = self.pick_a_spell(magic_only=True)
        if self.degree:
            learnrate = self.degree
        else:
            learnrate = 0.25

        try:
            learnrate = int(learnrate / rank) + 1
            learnrate = min(learnrate, 5)
        except ZeroDivisionError:
            learnrate = 5

        self.features['learnrate'] = learnrate
        self.features['learnspell'] = spell.spellid
        #WC - added in learn rate for clarity
        self.mutation_log['Spell learn rate'] = spell.name + " " + str(learnrate) + "x"

    def get_specialaction(self, new_action):

        #255 is listed as "Uses more MP" but is never actually applied in vanilla game. 255 is used for many consumables
        special_descriptions = ["Can steal", "Atma", "X-kill", "Man eater", "Drain HP", "Drain MP", "Uses some MP", "Random throw",
                                "Dice", "Valiant", "Wind Attack", "Heals Target", "Slice Kill", "Fragile wpn", "Uses more MP", ]
        s = special_descriptions[new_action-1]

        return s

    def mutate_special_action(self):
        if self.features['specialaction'] & 0xf0 != 0 or not self.is_weapon:
            return

        new_action = random.randint(1, 0xf)
        if new_action == 0xA:  # make random valiant knife effect rare
            new_action = random.randint(1, 0xf)

        if new_action == 9:  # no random dice effect
            return

        self.mutation_log["Special Effect"] = self.get_specialaction(new_action)

        self.features['specialaction'] = (new_action << 4) | (self.features['specialaction'] & 0x0f)
        self.mutate_name()

    def mutate_stats(self, itemstats1="n", itemstats2="n"):
        if self.is_consumable:
            return

        #WC todo - should only print this if they got changed
        #self.mutation_log["original power/def"] = self.features['power']
        #self.mutation_log["original hitrate/mdef"] = self.features['hitmdef']

        ###get the difference between 255 and current power. pick between the lower of the two: current power, that difference
        ###divide that by 3, round down. 
        ###power = current power - difference
        ###power = current power + (0 to diff) + (0 to diff)
        ###items with values closer to 127 get the most variation
        def mutate_power_hitmdef():
            diff = min(self.features['power'], 0xFF - self.features['power'])
            diff = diff // 3
            self.features['power'] = self.features['power'] - diff
            self.features['power'] = self.features['power'] + random.randint(0, diff) + random.randint(0, diff)
            self.features['power'] = int(min(0xFF, max(0, self.features['power'])))   #ensures power is between 0 and 255

            self.mutation_log["power/def"] = self.features['power']

            if "Dice" in self.name:
                return

            diff = min(self.features['hitmdef'], 0xFF - self.features['hitmdef'])
            diff = diff // 3
            self.features['hitmdef'] = self.features['hitmdef'] - diff
            self.features['hitmdef'] = self.features['hitmdef'] + random.randint(0, diff) + random.randint(0, diff)
            self.features['hitmdef'] = int(min(0xFF, max(0, self.features['hitmdef'])))

            self.mutation_log["hitrate/mdef"] = self.features['hitmdef']

        #####WC - itemstats1
        if itemstats1 == "y":
            mutate_power_hitmdef()

            #WC - comment this out, just apply it once
            #apply this to everything, then apply it again 1/11 of the time
            #mutate_power_hitmdef()
            #while random.randint(0, 10) == 10:
                #mutate_power_hitmdef()
        #####WC - itemstats1
                
        #byte references the 4th digit, 0 = positive, 1 = negative
        #nibble is the value from 1 to 7
        def mutate_nibble(byte, left=False, limit=7):
            if left:
                nibble = (byte & 0xf0) >> 4
                byte = byte & 0x0f
            else:
                nibble = byte & 0x0f   #0F = 15
                byte = byte & 0xf0     #F0 = 240

            value = nibble & 0x7
            if nibble & 0x8:
                value = value * -1

            #there is a 1/6 chance that the value will be modified by either 1 or -1
            while random.randint(1, 6) == 6:
                value += random.choice([1, -1])

            value = max(-limit, min(value, limit))   #ensure the value is between -7 and 7
            nibble = abs(value)
            if value < 0:
                nibble = nibble | 0x8

            if left:
                return byte | (nibble << 4)
            return byte | nibble

        #in binary reprsentation the first 3 digits represent 1 to 7, the 4th digit being 1 means negative
        #digits 5-8 represent 1 to 7 for the next stat, the 4th digit being 1 means negative

        #################modified the following section to get more details in the log

        if itemstats2 == "y":
            print_vigor = self.features['speedvigor'] & 15
            vigor_value = print_vigor & 7
            if print_vigor >> 3 == 1:
                vigor_value = -vigor_value
        
            print_speed = self.features['speedvigor'] & 240
            print_speed = print_speed >> 4
            speed_value = print_speed & 7
            if print_speed >> 3 == 1:
                speed_value = -speed_value

            self.mutation_log["original vigor"] = vigor_value
            self.mutation_log["original speed"] = speed_value
            
            self.features['speedvigor'] = mutate_nibble(self.features['speedvigor'])
            self.features['speedvigor'] = mutate_nibble(self.features['speedvigor'], left=True)

            print_vigor = self.features['speedvigor'] & 15
            vigor_value = print_vigor & 7
            if print_vigor >> 3 == 1:
                vigor_value = -vigor_value
        
            print_speed = self.features['speedvigor'] & 240
            print_speed = print_speed >> 4
            speed_value = print_speed & 7
            if print_speed >> 3 == 1:
                speed_value = -speed_value

            self.mutation_log["new vigor"] = vigor_value
            self.mutation_log["new speed"] = speed_value
            

            print_stamina = self.features['magstam'] & 15
            stamina_value = print_stamina & 7
            if print_stamina >> 3 == 1:
                stamina_value = -stamina_value
        
            print_mag = self.features['magstam'] & 240
            print_mag = print_mag >> 4
            mag_value = print_mag & 7
            if print_mag >> 3 == 1:
                mag_value = -mag_value

            self.mutation_log["original magpwr"] = mag_value
            self.mutation_log["original stamina"] = stamina_value
            
            self.features['magstam'] = mutate_nibble(self.features['magstam'])
            self.features['magstam'] = mutate_nibble(self.features['magstam'], left=True)

            print_stamina = self.features['magstam'] & 15
            stamina_value = print_stamina & 7
            if print_stamina >> 3 == 1:
                stamina_value = -stamina_value
        
            print_mag = self.features['magstam'] & 240
            print_mag = print_mag >> 4
            mag_value = print_mag & 7
            if print_mag >> 3 == 1:
                mag_value = -mag_value

            self.mutation_log["new magpwr"] = mag_value
            self.mutation_log["new stamina"] = stamina_value
            
                
            #################log testing

            evade, mblock = self.evade, self.mblock

            #self.mutation_log["evade"] = self.evade
            #self.mutation_log["mblock"] = self.mblock
            #self.features['mblockevade'] = evade | (mblock << 4)
            print_evade = 0
            print_mblock = 0
            if evade > 5:
                print_evade = -(evade - 5)
            else:
                print_evade = evade
            if mblock > 5:
                print_mblock = -(mblock - 5)
            else:
                print_mblock = mblock
            self.mutation_log["original evade"] = print_evade * 10
            self.mutation_log["original mblock"] = print_mblock * 10

            #########WC - comment out to leave evade/mblock the same
            if 1 == 1:
                def evade_is_screwed_up(value):
                    #1/8 chance that
                    #if nothing, becomes +10 or -10
                    #if 50, becomes 40
                    #if -10, becomes -20 or 0
                    #otherwise, add +10 or -10

                    #because of the while loop, there is a repeating chance for this to occur
                    while random.randint(1, 8) == 8:
                        if value == 0:
                            choices = [1, 6]
                        elif value in [5, 0xA]:
                            choices = [-1]
                        elif value == 6:
                            choices = [1, -6]
                        else:
                            choices = [1, -1]
                        value += random.choice(choices)
                    return value

                evade = evade_is_screwed_up(evade)
                mblock = evade_is_screwed_up(mblock)
                self.features['mblockevade'] = evade | (mblock << 4)

                if evade > 5:
                    print_evade = -(evade - 5)
                else:
                    print_evade = evade
                if mblock > 5:
                    print_mblock = -(mblock - 5)
                else:
                    print_mblock = mblock
                self.mutation_log["new evade"] = print_evade * 10
                self.mutation_log["new mblock"] = print_mblock * 10
                self.mutation_log['mblockevade'] =evade | (mblock << 4)
            #########WC - ^ comment out to leave evade/mblock the same ^
        #end check for itemstats2 == "y"


    def mutate_price(self, undo_priceless=False, crazy_prices=False):
        if crazy_prices:
            if self.itemid == 250:
                self.price = random.randint(250, 500)
            else:
                self.price = random.randint(20, 500)
            return
        if self.price <= 2:
            if undo_priceless:
                self.price = self.rank()
            else:
                return

        normal = self.price // 2
        self.price += random.randint(0, normal) + random.randint(0, normal)
        while random.randint(1, 10) == 10:
            self.price += random.randint(0, normal) + random.randint(0, normal)

        zerocount = 0
        while self.price > 100:
            self.price = self.price // 10
            zerocount += 1

        while zerocount > 0:
            self.price = self.price * 10
            zerocount += -1

        self.price = min(self.price, 65000)

    def mutate(self, always_break=False, crazy_prices=False, extra_effects=False, wild_breaks=False, no_breaks=False, unbreakable=False,
               itemstats1="n", itemstats2="n", itembreakproc="n", itemteacher="n", itemelemental="n",
               itemspecial="n", itemfeature="n", itemheavy="n", item_wild_breaks="n", item_extra_effects="n"):
        global changed_commands

        ########WC - update BC flags
        if item_wild_breaks == "y":
            wild_breaks=True
        if item_extra_effects == "y":
            extra_effects=True
            
        #optional, pass in itemstats1, itemstats2
        self.mutate_stats(itemstats1, itemstats2)

        ######WC - leave prices the same
        #self.mutate_price(crazy_prices=crazy_prices)
        broken, learned = False, False

        #####WC - don't really stuff to break randomly. always_break=False
        if always_break:
            self.mutate_break_effect(always_break=True, wild_breaks=wild_breaks)
            broken = True

        ########WC - experimental. command changer
        if item_wild_breaks == "y":
            #disable in WC
            if 0 == 1:            
                for command, itemids in list(break_unused_dict.items()):
                    if command in changed_commands and self.itemid in itemids:
                        self.mutate_break_effect(wild_breaks=wild_breaks)
                        broken = True

        #######WC sprint shoes???????
        #if self.itemid == 0xE6:
        if 0 == 1 and self.itemid == 0xE6:
            self.mutate_learning()
            learned = True
        #######WC sprint shoes???????
            
        #special_actions: ["Can steal", "Atma", "X-kill", "Man eater", "Drain HP", "Drain MP", "Uses some MP", "Random throw",
                                #"Dice", "Valiant", "Wind Attack", "Heals Target", "Slice Kill", "Fragile wpn", "Uses more MP", ]
        #elemental changes: (["fire", "ice", "lightning", "poison", "wind", "pearl", "earth", "water"])}
        #repeated 20% chance

        #######section to force changes
        #force a chance for proc on every item
        #self.mutate_break_effect(wild_breaks=wild_breaks)

        #############end section to force changes

        ########WC - added WC flags, increase change of loop entry from 20% to 60%
        #while random.randint(1, 5) == 5:
        while random.randint(1, 5) >= 3:
        #while (random.randint(1, 5) == 5 and 0 == 1):  #uncomment to stop most randomization
            x = random.randint(0, 99)

            #10% chance for special action, "Special Effect" in log
            if x < 10:
                if itemspecial == "y":
                    self.mutate_special_action()

            #10% chance for spell learning
            #if 10 <= x < 20 and not learned:
            if 10 <= x < 40 and not learned:  #changed for WC
                if itemteacher == "y":
                    self.mutate_learning()
                    self.mutate_name()

            #30% chance for a proc effect (or a break effect???)
            #if 20 <= x < 50 and not broken:
            if 40 <= x < 60 and not broken:   #changed for WC
                if itembreakproc == "y":
                    self.mutate_break_effect(wild_breaks=wild_breaks)
                    broken = True

            #30% chance for changes to elemental properties
            #if 50 <= x < 80:
            if 60 <= x < 95:    #changed for WC
                if itemelemental == "y":
                    self.mutate_elements()

            #20% chance of something from: get_feature(self, feature, feature_byte, nochange):
            #this includes Command Changes
            if x >= 95:
                if itemfeature == "y":
                    self.mutate_feature()


        #5% chance to randomly set something as "heavy" if it isn't, applies to Merit Award
        if not self.heavy and random.randint(1, 20) == 20:
            if itemheavy == "y":
                self.heavy = True

        #further chance of stuff
        #Command Changer???
        #WC - use WC extra_effects flag
        #if extra_effects:
        if item_extra_effects == "y":
            if random.randint(1, 3) == 3:
                self.mutate_special_action()

            if random.randint(1, 2) == 2:
                self.mutate_feature()
                #pass
            while random.randint(1, 3) == 3:
                self.mutate_feature()
                #pass

        #WC - no_breaks off, unbreakable off
        if no_breaks:
            self.mutate_break_effect(no_breaks=no_breaks)
        if unbreakable:
            self.mutate_break_effect(unbreakable=unbreakable)

    def mutate_name(self):
        #questionablecontent flag is always off for now
        
        if Options_.is_code_active("questionablecontent") and not self.is_consumable and '?' not in self.name:
            self.name = self.name[:11] + '?'
            # Index on self.dataname is [1:] because the first character determines the
            #   equipment symbol (helmet/shield/etc).
            self.dataname[1:] = name_to_bytes(self.name, len(self.name))

    #how is this 
    def rank(self):
        if self._rank:
            return self._rank

        if self.price > 10:
            return self.price

        bl = 0
        if self.is_consumable:
            baseline = 5000
            #otherproperties: 0x08 is breaks? 0x10 is doesnt break?
            if self.features['otherproperties'] & 0x08:
                bl += 25
            if self.features['otherproperties'] & 0x10:
                bl += 75

            #rods maybe?
            if self.features['otherproperties'] & 0x80:
                bl *= (self.features['power'] / 16.0) * 2

            #targeting?
            if self.features['targeting'] & 0x20:
                bl *= 2

            #special features?
            if bl == 0 and self.features['specialaction']:
                bl += 50
        else:

            #imp stuff goes to 0, oitherwise set to 25k with random -5 to +5 variance?
            if self.imp_only:
                baseline = 0
            else:
                baseline = 25000 + random.randint(-5, 5)

            if not self.is_tool and not self.is_relic:
                power = self.features['power']
                if power < 2:
                    power = 250
                bl += power

                if self.evade in range(2, 6):
                    bl += (self.evade ** 2) * 25

                if self.mblock in range(2, 6):
                    bl += (self.mblock ** 2) * 25

                if self.evade == self.mblock == 1:
                    bl += 100

                if (self.is_armor and (self.features['elemabsorbs'] or
                                       self.features['elemnulls'] or
                                       self.features['elements'])):
                    void = (self.features['elemabsorbs'] |
                            self.features['elemnulls'])
                    bl += (100 * bin(void).count('1'))
                    bl += (25 * bin(self.features['elements']).count('1'))

            #"Bat. Pwr +1/4", "Mag. Pwr +1/2", "+1/4 HP", "+1/2 HP", "+1/8 HP", "+1/4 MP", "+1/2 MP", "+1/8 MP"
            if self.features['statboost1'] & 0x4b:
                bl += 50

            #MP cost = 1 I guess?
            if self.features['statboost2'] & 0x40:
                # Economizer
                bl += 1001

            #"Initiative", "Vigilance", "Command Changer","Command Changer", "Command Changer", "Command Changer","Command Changer", "Super Jump"
            if self.features['special1'] & 0x80:
                bl += 100

            if self.features['special1'] & 0x08:
                bl += 500

            #"Fight -> X-Fight", "Can counter","Random Evade", "Use weapon 2-handed","Can equip 2 weapons", "Can equip anything","Cover", "Step regen"
            if self.features['special2'] & 0x10:
                bl += 100

            if self.features['special2'] & 0x21:
                # Merit Award and Offering
                bl += 1000

            if self.features['specialaction'] & 0xf0 == 0xa0:
                # Valiant Knife
                bl += 1000

            #"Fight -> X-Fight", "Can counter", "Random Evade","Use weapon 2-handed", "Can equip 2 weapons","Can equip anything", "Cover", "Step regen"
            if self.features['special3'] & 0x08:
                bl += 300

            #charm/moogle/sprint
            if self.features['fieldeffect'] & 0x02:
                bl += 300

            #positive auto status
            if self.features['statusacquire3'] & 0xeb:
                bl += 100 * bin(self.features['statusacquire3']).count('1')

            #negative auto-status
            if self.features['statusacquire2'] & 0xf9:
                bl += -50 * bin(self.features['statusacquire2']).count('1')

            if self.itemid == 0x66:
                # cursed shield
                bl += 666

            #fixed dice
            if self.itemid == 0x52:
                bl += 277

        baseline += (bl * 100)
        self._rank = int(baseline)
        return self.rank()


NUM_CHARS = 14
CHAR_MASK = 0x3fff
IMP_MASK = 0x4000
UMARO_ID = 13


def reset_equippable(items, characters, numchars=NUM_CHARS):
    global changed_commands
    prevents = [i for i in items if i.prevent_encounters]
    for item in prevents:
        while True:
            test = 1 << random.randint(0, numchars - 1)
            if item.itemid == 0xDE or not (CHAR_MASK & item.equippable):
                item.equippable = test
                break

            if test & item.equippable:
                test |= IMP_MASK
                item.equippable &= test
                break

    items = [i for i in items if not (i.is_consumable or i.is_tool or i.prevent_encounters)]
    new_weaps = list(range(numchars))
    random.shuffle(new_weaps)
    new_weaps = dict(list(zip(list(range(numchars)), new_weaps)))

    for item in items:
        if numchars == 14 and random.randint(1, 10) == 10:
            # for umaro's benefit
            item.equippable |= 0x2000

        if item.is_weapon:
            equippable = item.equippable
            item.equippable &= IMP_MASK
            for i in range(numchars):
                if equippable & (1 << i):
                    item.equippable |= (1 << new_weaps[i])
        elif item.is_relic:
            if random.randint(1, 15) == 15:
                item.equippable = 1 << (random.randint(0, numchars - 1))
                while random.randint(1, 3) == 3:
                    item.equippable |= (1 << (random.randint(0, numchars - 1)))
            else:
                item.equippable = CHAR_MASK

    charequips = []
    valid_items = [i for i in items
                   if (not i.is_weapon and not i.is_relic and not i.equippable & 0x4000)]
    for c in range(numchars):
        myequips = []
        for i in valid_items:
            if i.equippable & (1 << c):
                myequips.append(True)
            else:
                myequips.append(False)
        random.shuffle(myequips)
        charequips.append(myequips)

    for item in valid_items:
        item.equippable &= 0xc000

    random.shuffle(charequips)
    for c in range(numchars):
        assert len(valid_items) == len(charequips[c])
        for equippable, item in zip(charequips[c], valid_items):
            if equippable:
                item.equippable |= (1 << c)

    if random.randint(1, 3) == 3:
        weaponstoo = True
    else:
        weaponstoo = False

    for item in items:
        if item.equippable == 0:
            if not weaponstoo:
                continue
            item.equippable |= (1 << random.randint(0, numchars - 1))

    paladin_equippable = None
    for item in items:
        if item.itemid in [0x66, 0x67]:
            if paladin_equippable is not None:
                item.equippable = paladin_equippable
            else:
                paladin_equippable = item.equippable

    if 0x10 not in changed_commands:
        for item in items:
            if item.itemid == 0x1C:
                rage_chars = [c for c in characters if
                              0x10 in c.battle_commands]
                rage_mask = 0
                for c in rage_chars:
                    rage_mask |= (1 << c.id)
                rage_mask |= (1 << 12)  # gogo
                if item.equippable & rage_mask:
                    invert_rage_mask = 0xFFFF ^ rage_mask
                    item.equippable &= invert_rage_mask
                assert not item.equippable & rage_mask

    return items


sperelic = {0x04: (0x25456, 0x2545B),
            0x08: (0x25455, 0x2545A),
            0x10: (0x25454, 0x25459),
            0x20: (0x25453, 0x25458),
            0x40: (0x25452, 0x25457)}

sperelic2 = {0x04: (0x3619C, 0x361A1),
             0x08: (0x3619B, 0x361A0),
             0x10: (0x3619A, 0x3619F),
             0x20: (0x36199, 0x3619E),
             0x40: (0x36198, 0x3619D)}

#Fight, Revert, Row, Def, Summon
#invalid_commands = [0x00, 0x04, 0x14, 0x15, 0x19, 0xFF]
#WC - include Morph (0x03), Leap (0x11)
invalid_commands = [0x00, 0x03, 0x04, 0x11, 0x14, 0x15, 0x19, 0xFF]

def reset_cursed_shield(fout):
    cursed = get_item(0x66)
    cursed.equippable = cursed.equippable & 0x0FFF
    cursed.write_stats(fout)


def reset_special_relics(items, characters, fout):
    global changed_commands

    #print("changed commands: ")
    #print(changed_commands)
    #input("A")
    
    characters = [c for c in characters if c.id < 14]
    changedict = {}
    loglist = []

    hidden_commands = set(range(0, 0x1E)) - set(invalid_commands)
    for c in characters:
        hidden_commands = hidden_commands - set(c.battle_commands)

    #2/3 chance for Possess to be removed
    if 0x1D in hidden_commands and random.randint(1, 3) != 3:
        hidden_commands.remove(0x1D)

#{1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 23, 24, 26, 27, 28}

    #print(hidden_commands)
    #input("X")

    flags = [0x04, 0x08, 0x10, 0x20, 0x40]
    random.shuffle(flags)
    for flag in flags:
        #print(flag)
        if changedict:
            donebefore, doneafter = tuple(zip(*list(changedict.values())))
            donebefore, doneafter = set(donebefore), set(doneafter)
        else:
            donebefore, doneafter = set([]), set([])
        while True:
            #0x08 = magic replacements -> fight, item, magic, mimic????
            if flag == 0x08:
                candidates = set([0x0, 0x1, 0x2, 0x12])
            else:
                candidates = list(range(0, 0x1E))
                candidates = set(candidates) - set([0x04, 0x14, 0x15, 0x19])
                #remove Revert, Row, Def, Summon

            if random.randint(1, 5) != 5:
                candidates = candidates - donebefore

            candidates = sorted(candidates)
            #print(candidates)
            #input("X")
            before = random.choice(candidates)

            #print("Before: " + str(before))

            #if before = "Fight"
            if before == 0:
                tempchars = [c for c in characters]
            else:
                #if "before" command isn't Fight
                #tempchars gets all the characters that have the "before" command
                #print(c.name)
                #print(c.battle_commands)
                #input("before")
                tempchars = [c for c in characters if before in c.battle_commands]

            if not tempchars:
                #go back to beginning of while loop
                continue

            #print(tempchars)
            #input("move")

            #get all the commands currently not used
            unused = set(range(0, 0x1E)) - set(invalid_commands)
            if len(tempchars) <= 4:
                for t in tempchars:
                    unused = unused - set(t.battle_commands)

            if flag == 0x08:
                unused = unused - changed_commands

            if set(hidden_commands) & set(unused):
                unused = set(hidden_commands) & set(unused)

            if before in unused:
                unused.remove(before)

            if random.randint(1, 5) != 5:
                unused = unused - doneafter

            # Umaro can't get magic/x-magic.
            for t in tempchars:
                if t.id == UMARO_ID:
                    unused = unused - {0x02, 0x17}
                    break

            if not unused:
                continue

            #pick a replacement command for the "before" command
            after = random.choice(sorted(unused))
            if after in hidden_commands:
                hidden_commands.remove(after)

            #not sure what these addresses are
            for ptrdict in [sperelic, sperelic2]:
                beforeptr, afterptr = ptrdict[flag]
                fout.seek(beforeptr)
                fout.write(bytes([before]))
                fout.seek(afterptr)
                fout.write(bytes([after]))
            break
        changedict[flag] = (before, after)

    #print(changedict)
    #input("Z")

    for item in items:
        if (item.is_consumable or item.is_tool or
                not item.features['special1'] & 0x7C):
            continue

        if item.itemid == 0x67:
            continue

        item.equippable &= IMP_MASK
        item.equippable |= 1 << 12  # gogo
        for flag in [0x04, 0x08, 0x10, 0x20, 0x40]:
            if flag & item.features['special1']:
                before, after = changedict[flag]
                tempchars = [c for c in characters
                             if before in c.battle_commands]
                for t in tempchars:
                    item.equippable |= (1 << t.id)

                item.write_stats(fout)
                loglist.append((item.name, before, after))

    return loglist


def reset_rage_blizzard(items, umaro_risk, fout):
    for item in items:
        if item.itemid not in [0xC5, 0xC6]:
            continue

        item.equippable = 1 << (umaro_risk.id)
        item.write_stats(fout)


def items_from_table(tablefile):
    items = []
    for line in open(tablefile):
        line = line.strip()
        if line[0] == '#':
            continue

        while '  ' in line:
            line = line.replace('  ', ' ')
        c = ItemBlock(*line.split(','))
        items.append(c)
    return items


def get_items(filename=None, allow_banned=False):
    global itemdict
    if itemdict:
        to_return = [i for i in list(itemdict.values()) if i]
        if not allow_banned:
            to_return = [i for i in to_return if not i.banned]
        return to_return

    items = items_from_table(ITEM_TABLE)
    for i in items:
        i.read_stats(filename)

    for n, i in enumerate(items):
        i.set_degree(n / float(len(items)))
        itemdict[i.itemid] = i
    itemdict[0xFF] = None

    return get_items()


def get_item(itemid, allow_banned=False):
    global itemdict
    item = itemdict[itemid]
    if item and item.banned:
        if allow_banned:
            return item
        return None
    return item


def unbanItems():
    global itemdict
    try:
        for x in range(0, len(itemdict)):
            item = itemdict[x]
            if item != None:
                item.banned = False
    except Exception as e:
        traceback.print_exc()


def get_secret_item():
    item = get_item(0, allow_banned=True)
    if not item.banned:
        item = get_item(0xEF)
    return item


def get_ranked_items(filename=None, allow_banned=False):
    items = get_items(filename, allow_banned)
    return sorted(items, key=lambda i: i.rank())


#running this causes many problems with Esper equipability
def unhardcode_tintinabar(fout):
    # Apply Lenophis's unhardcoded tintinabar patch (solo version)
    tintinabar_sub = Substitution()

#C0/4A57:	2940    	AND #$40
#C0/4A59:	F070    	BEQ $4ACB
#C0/4A5B:	BD5018  	LDA $1850,X		(Load steup of current parties)
#C0/4A5E:	2907    	AND #$07		
#C0/4A60:	CD6D1A  	CMP $1A6D		(Compare to the active party)
#C0/4A63:	D066    	BNE $4ACB
#C0/4A65:	B91416  	LDA $1614,Y		(Load character's statuses)
#C0/4A68:	29C2    	AND #$C2		
#C0/4A6A:	D027    	BNE $4A93
#C0/4A6C:	B92316  	LDA $1623,Y		(Load character's relic 1)
#C0/4A6F:	C9E5    	CMP #$E5		(Is it Tintinabar?)
#C0/4A71:	F007    	BEQ $4A7A		(Branch if it is)
#C0/4A73:	B92416  	LDA $1624,Y		(Load character's relic 2)
#C0/4A76:	C9E5    	CMP #$E5		(Is it Tintinabar?)
#C0/4A78:	D019    	BNE $4A93		(Branch if it's not)
#C0/4A7A:	20E8AE  	JSR $AEE8
#C0/4A7D:	B91C16  	LDA $161C,Y		(Load character's stamina)
#C0/4A80:	4A      	LSR A			(* 2)
#C0/4A81:	4A      	LSR A			(Now * 4)
#C0/4A82:	C221    	REP #$21
#C0/4A84:	790916  	ADC $1609,Y		(Add current HP to Stamina * 4)
#C0/4A87:	C51E    	CMP $1E
#C0/4A89:	9002    	BCC $4A8D
#C0/4A8B:	A51E    	LDA $1E
#C0/4A8D:	990916  	STA $1609,Y		(Store to current HP)
    
    tintinabar_sub.set_location(0x4A57)
    tintinabar_sub.bytestring = bytes(
        [0x89, 0x40, 0xF0, 0x5C, 0x29, 0x07, 0xCD, 0x6D, 0x1A, 0xD0, 0x55, 0x20, 0xE8, 0xAE, 0xB9, 0x14, 0x16, 0x89,
         0xC2, 0xD0, 0x4B, 0x20, 0x0D, 0xDF, 0xF0, 0x19, 0xB9, 0x1C, 0x16, 0x4A, 0x4A, 0xC2, 0x21, 0x29, 0xFF, 0x00,
         0x79, 0x09, 0x16, 0xC5, 0x1E, 0x90, 0x02, 0xA5, 0x1E, 0x99, 0x09, 0x16, 0x7B, 0xE2, 0x20, 0xB9, 0x14, 0x16,
         0x29, 0x04, 0xF0, 0x26, 0x7B, 0xA9, 0x0F, 0x8D, 0xF0, 0x11, 0xC2, 0x20, 0xEB, 0x8D, 0x96, 0x07, 0xC2, 0x20,
         0xA5, 0x1E, 0x4A, 0x4A, 0x4A, 0x4A, 0x4A, 0x85, 0x1E, 0xB9, 0x09, 0x16, 0x38, 0xE5, 0x1E, 0xF0, 0x02, 0xB0,
         0x02, 0x7B, 0x1A, 0x99, 0x09, 0x16, 0xC2, 0x21, 0x98, 0x69, 0x25, 0x00, 0xA8, 0x7B, 0xE2, 0x20, 0xE8, 0xE0,
         0x10, 0x00, 0xD0, 0x8D, 0xFA, 0x86, 0x24, 0xFA, 0x86, 0x22, 0xFA, 0x86, 0x20, 0xFA, 0x86, 0x1E, 0x28, 0x6B])
    tintinabar_sub.write(fout)

    #not sure
    tintinabar_sub.set_location(0x6CF8)
    tintinabar_sub.bytestring = bytes(
        [0x8C, 0x48, 0x14, 0x64, 0x1B, 0xB9, 0x67, 0x08, 0x0A, 0x10, 0x11, 0x4A, 0x29, 0x07, 0xCD, 0x6D, 0x1A, 0xD0,
         0x09, 0xA5, 0x1B, 0x22, 0x77, 0x0E, 0xC2, 0x20, 0xF6, 0xDE, 0xC2, 0x21, 0x98, 0x69, 0x29, 0x00, 0xA8, 0xE2,
         0x20, 0xE6, 0x1B, 0xC0, 0x90, 0x02, 0xD0, 0xD9, 0x7B, 0x60])
    tintinabar_sub.write(fout)

    #normally unused space
    tintinabar_sub.set_location(0xDEF6)
    tintinabar_sub.bytestring = bytes(
        [0xAD, 0xD8, 0x11, 0x10, 0x11, 0xA5, 0x1B, 0x5A, 0x1A, 0xA8, 0xC2, 0x20, 0x38, 0x7B, 0x2A, 0x88, 0xD0, 0xFC,
         0x0C, 0x48, 0x14, 0x7A, 0x60, 0x8C, 0x04, 0x42, 0xA9, 0x25, 0x8D, 0x06, 0x42, 0x22, 0xD4, 0x4A, 0xC0, 0x7B,
         0xAD, 0x14, 0x42, 0xDA, 0x1A, 0xAA, 0xC2, 0x20, 0x38, 0x7B, 0x2A, 0xCA, 0xD0, 0xFC, 0xFA, 0x2C, 0x48, 0x14,
         0xE2, 0x20, 0x60])
    tintinabar_sub.write(fout)

    #menu program
    #05: Sustain main menu
    #C3/1DA4:	204835  	JSR $3548      ; Redraw time
    #C3/1DA7:	A508    	LDA $08        ; No-autofire keys
    #C3/1DA9:	8980    	BIT #$80       ; Pushing A?
    #C3/1DAB:	F003    	BEQ $1DB0      ; Branch if not
    #C3/1DAD:	4C622E  	JMP $2E62      ; Handle selection
    tintinabar_sub.set_location(0x31DA9)
    tintinabar_sub.bytestring = bytes(
        [0x10, 0x03, 0x4C, 0x62, 0x2E, 0xA5, 0x09, 0x89, 0x02, 0xF0, 0x03, 0x4C, 0xC6, 0x2E, 0x10, 0x0F, 0x9C, 0x05,
         0x02, 0x20, 0xA9, 0x0E, 0x20, 0xC9, 0x1D, 0x7B, 0x3A, 0x85, 0x27, 0x64, 0x26, 0x60, 0x9C, 0xDF, 0x11, 0x9C,
         0x48, 0x14, 0x9C, 0x49, 0x14, 0xA2, 0x03, 0x00, 0xB5, 0x69, 0x30, 0x07, 0x22, 0x77, 0x0E, 0xC2, 0x20, 0x6C,
         0xF1, 0xCA, 0x10, 0xF2, 0x60, 0x00, 0xD0, 0xF0, 0x60])
    tintinabar_sub.write(fout)

    #normally unused space
    tintinabar_sub.set_location(0x3F16C)
    tintinabar_sub.bytestring = bytes(
        [0xAD, 0xD8, 0x11, 0x10, 0x12, 0x7B, 0xB5, 0x69, 0x1A, 0xA8, 0x38, 0x7B, 0xC2, 0x20, 0x2A, 0x88, 0xD0, 0xFC,
         0x0C, 0x48, 0x14, 0xE2, 0x20, 0x60])
    tintinabar_sub.write(fout)
