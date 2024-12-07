
#!/usr/bin/env python3

import configparser
from time import time, sleep, gmtime

import re
import sys
from sys import argv
from shutil import copyfile
import os
from hashlib import md5

#added for formation management
from typing import BinaryIO, Callable, Dict, List, Set, Tuple


#added for musicrandomizer
import music.musicrandomizer
#^ added for musicrandomizer

#added for command management
import character
from character import get_characters, get_character, equip_offsets
#^ added for command management

#added for enemy sprite swap
import multiprocessing
from remonsterate.remonsterate import remonsterate
#^ added for enemy sprite swap

from formationrandomizer import (REPLACE_FORMATIONS, KEFKA_EXTRA_FORMATION,
                                 NOREPLACE_FORMATIONS, get_formations,
                                 get_fsets, get_formation, Formation,
                                 FormationSet)
from itemrandomizer import (reset_equippable, get_ranked_items, get_item,
                            reset_special_relics, reset_rage_blizzard,
                            reset_cursed_shield, unhardcode_tintinabar,
                            ItemBlock)
from locationrandomizer import (get_locations, get_location, get_zones, get_npcs, randomize_forest)
from menufeatures import (improve_item_display, improve_gogo_status_menu, improve_rage_menu,
                          show_original_names, improve_dance_menu, y_equip_relics, fix_gogo_portrait)
from monsterrandomizer import (MonsterBlock, REPLACE_ENEMIES, MonsterGraphicBlock, get_monsters,
                               get_metamorphs, get_ranked_monsters,
                               shuffle_monsters, get_monster, read_ai_table,
                               change_enemy_name, randomize_enemy_name,
                               get_collapsing_house_help_skill)
from musicinterface import randomize_music, manage_opera, get_music_spoiler, music_init#, get_opera_log
from skillrandomizer import (SpellBlock, CommandBlock, SpellSub, ComboSpellSub,
                             RandomSpellSub, MultipleSpellSub, ChainSpellSub,
                             get_ranked_spells, get_spell)
from options import ALL_MODES, ALL_FLAGS, Options_
from patches import (allergic_dog, banon_life3, vanish_doom, evade_mblock,
                     death_abuse, no_kutan_skip, show_coliseum_rewards,
                     cycle_statuses, no_dance_stumbles, fewer_flashes)
from utils import (COMMAND_TABLE, LOCATION_TABLE, LOCATION_PALETTE_TABLE,
                   FINAL_BOSS_AI_TABLE, SKIP_EVENTS_TABLE, DANCE_NAMES_TABLE,
                   DIVERGENT_TABLE,
                   get_long_battle_text_pointer,
                   Substitution, shorttexttable, name_to_bytes,
                   hex2int, int2bytes, read_multi, write_multi,
                   generate_swapfunc, shift_middle, get_palette_transformer,
                   battlebg_palettes, set_randomness_multiplier,
                   mutate_index, utilrandom as random, open_mei_fallback,
                   AutoLearnRageSub)

#added for musicrandomizer
from musicinterface import randomize_music, manage_opera, get_music_spoiler, music_init
#^ added for musicrandomizer

VERSION = "4"
BETA = False
VERSION_ROMAN = "IV"
if BETA:
    VERSION_ROMAN += " BETA"
TEST_ON = False
TEST_SEED = "44.abcefghijklmnopqrstuvwxyz-partyparty.42069"
TEST_FILE = "program.rom"
seed, flags = None, None
seedcounter = 1
sourcefile, outfile = None, None
fout = None


NEVER_REPLACE = ["fight", "item", "magic", "row", "def", "magitek", "lore",
                 "jump", "mimic", "xmagic", "summon", "morph", "revert"]
RESTRICTED_REPLACE = ["throw", "steal"]
ALWAYS_REPLACE = ["leap", "possess", "health", "shock"]
FORBIDDEN_COMMANDS = ["leap", "possess"]

MD5HASH = "e986575b98300f721ce27c180264d890"


TEK_SKILLS = (
    # [0x18, 0x6E, 0x70, 0x7D, 0x7E] +
    list(range(0x86, 0x8B)) +
    [0xA7, 0xB1] +
    list(range(0xB4, 0xBA)) +
    [0xBF, 0xCD, 0xD1, 0xD4, 0xD7, 0xDD, 0xE3])


namelocdict = {}
changed_commands = set([])

randlog = {}


####################WC - global variables for options
#itemstats1 = "n"
#itemstats2 = "n"
#itembreakproc = "n"
#itemteacher = "n"
#itemelemental = "n"
#itemspecial = "n"
#itemfeature = "n"
#itemheavy = "n"
#item_wild_breaks = "n"
#item_extra_effects = "n"

#monsterstats1 = "n"
#monsterstats2 = "n"
#monstermisc = "n"
#monsterautostatus = "n"
#monsterelemental = "n"
#monsterspecials = "n"
#monsters_darkworld = "n"
#monsterscripts = "n"
#monstercontrol = "n"
#monsterdrops = "n"
#monstersteals = "n"
#monstermorphs = "n"

#command_no_guarantee_itemmagic = "n"
#command_more_duplicates = "n"
####################WC - global variables for options


def log(text, section):
    global randlog
    if section not in randlog:
        randlog[section] = []
    if "\n" in text:
        text = text.split("\n")
        text = "\n".join([line.rstrip() for line in text])
    text = text.strip()
    randlog[section].append(text)


def get_logstring(ordering: List = None) -> str:
    global randlog
    s = ""
    if ordering is None:
        ordering = sorted([o for o in randlog if o is not None])
    ordering = [o for o in ordering if o is not None]

    for d in randlog[None]:
        s += d + "\n"

    s += "\n"
    sections_with_content = []
    for section in ordering:
        if section in randlog:
            sections_with_content.append(section)
            s += "-{0:02d}- {1}\n".format(len(sections_with_content), " ".join([word.capitalize()
                                        for word in section.split()]))
    for sectnum, section in enumerate(sections_with_content):
        datas = sorted(randlog[section])
        s += "\n" + "=" * 60 + "\n"
        s += "-{0:02d}- {1}\n".format(sectnum + 1, section.upper())
        s += "-" * 60 + "\n"
        newlines = False
        if any("\n" in d for d in datas):
            s += "\n"
            newlines = True
        for d in datas:
            s += d.strip() + "\n"
            if newlines:
                s += "\n"
    return s.strip()

def reseed():
    global seedcounter
    random.seed(seed + seedcounter)
    seedcounter += (seedcounter * 2) + 1

def rewrite_checksum(filename=None):
    if filename is None:
        filename = outfile
    MEGABIT = 0x20000
    f = open(filename, 'r+b')
    subsums = [sum(f.read(MEGABIT)) for _ in range(32)]
    checksum = sum(subsums) & 0xFFFF
    f.seek(0xFFDE)
    write_multi(f, checksum, length=2)
    f.seek(0xFFDC)
    write_multi(f, checksum ^ 0xFFFF, length=2)
    f.close()

class FreeBlock:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    @property
    def size(self):
        return self.end - self.start

    def unfree(self, start, length):
        end = start + length
        if start < self.start:
            raise Exception("Used space out of bounds (left)")
        if end > self.end:
            raise Exception("Used space out of bounds (right)")
        newfree = []
        if self.start != start:
            newfree.append(FreeBlock(self.start, start))
        if end != self.end:
            newfree.append(FreeBlock(end, self.end))
        self.start, self.end = None, None
        return newfree


def get_appropriate_freespace(freespaces, size):
    candidates = [c for c in freespaces if c.size >= size]
    if not candidates:
        raise Exception("Not enough free space")

    candidates = sorted(candidates, key=lambda f: f.size)
    return candidates[0]


def determine_new_freespaces(freespaces, myfs, size):
    freespaces.remove(myfs)
    fss = myfs.unfree(myfs.start, size)
    freespaces.extend(fss)
    return freespaces


#######original ultimate weapons patch. moved over to WC for now, which allows for WC equippability randomization to occur
#######prior to BC mods
####Look for:
####RegalCutlass, Crystal, Stout Spear, Mithril Claw, Kodachi, Kotetsu, Forged, Darts, Epee, Punisher, DaVinci Brsh, Boomerang
def ultimates(items: List[ItemBlock], changed_commands: Set[int]=None) -> List[ItemBlock]:
    from itemrandomizer import (set_item_changed_commands, extend_item_breaks)

    for i in items:
        convert = False
        #TERRA, LOCKE, CYAN, SHADOW 0-3
        #EDGAR, SABIN, CELES, STRAGO, RELM 4-8
        #SETZER, MOG, GAU, GOGO, UMARO 9-13
        #specify equippability:
        #i.equippable = 32769  #Terra
        #i.equippable = 32770  #Locke
        #i.equippable = 32772  #Cyan
        #32776  #Shadow
        #32784  #Edgar
        #32800  #Sabin
        #32832  #Celes
        #32896  #Strago
        #33024  #Relm
        #33280  #Setzer
        #33792  #Mog
        #34816  #Gau
        #36864  #Gogo
        #40960  #Umaro

        #Item name symbol:
        #Dirk - knife / shadow knife  216
        #MithrilBlade - sword  217
        #Partisan - spear  218
        #ashura  - katana  219
        #heal rod - rod  220
        #chocobo brsh - brush  221
        #morning star - special 222
        #cards - cards  223
        #metalknuckle - claw  224

        #weapon animation
        #Dirk: [39, 39, 24, 62, 54, 0, 148, 0]
        #Illumina: [92, 92, 32, 1, 55, 0, 164, 0]
        #Aura Lance: [93, 93, 43, 5, 51, 0, 168, 0]
        #Chocobo Brsh: [22, 22, 37, 4, 55, 0, 148, 0]
        #Flail: [25, 25, 25, 8, 25, 0, 218, 0]
        #Ragnarok: [30, 30, 32, 0, 55, 0, 164, 0]
        if i.name == "RegalCutlass":
            i.features['power'] = 250 
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 7 #+7 Str
            i.features['magstam'] = 112 #+7 Mag
            i.features['specialaction'] = 112 #Punisher effect, MP Crit.
            evade = 2
            mblock = 2
            i.features['mblockevade'] = evade | (mblock << 4) #20% evade, 20% mblock

            i.weapon_animation = bytes([92, 92, 32, 1, 55, 0, 164, 0]) #change animation to sword/illumina
            i.name = "Apocalypse"
            i.dataname[1:] = name_to_bytes(i.name, 12)

            convert = True
        if i.name == "Crystal":
            i.features['power']=220
            i.features['hitmdef']=180
            i.features['speedvigor'] = 115  #+3 Str +7 Spd
            i.features['magstam'] = 3    #+3 Sta
            evade = 3
            mblock = 2
            i.features['mblockevade'] = evade | (mblock << 4) #30% evade, 20% mblock
            
            i.features['elements'] = 16   #wind element
            i.features['breakeffect'] = 29  #0 = Fire, 1 = Ice, etc. Sleep = 29
            i.features["otherproperties"] = 198  #198 is the proc + swdtech/allows two hands/runic, shifted from vanilla
            i.name = "ZwillXBlade"

            i.weapon_animation = bytes([39, 39, 24, 62, 54, 0, 148, 0]) #change animation to dagger
            i.dataname[1:] = name_to_bytes(i.name, 12)
            i.dataname[0:1] = bytes([216])   #change icon to dagger

            convert = True
        if i.name == "Stout Spear":
            i.features['power'] = 235
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 55 #+7 Str +3 Spd
            i.features['magstam'] = 3 #+3 Sta
            i.name = "Longinus"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True
        #if i.name == "Mithril Claw":      #even though there is a space in the game name the space is removed in BC
        if i.name == "MithrilClaw":
            i.features['power'] = 245
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 7 #+7 Str
            i.features['magstam'] = 7 #+7 Sta
            evade = 3
            mblock = 0
            i.features['mblockevade'] = evade | (mblock << 4) #30% evade, 20% mblock
            i.features['elements'] = 32  #pearl element
            i.name = "Godhand"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True
        if i.name == "Kodachi":
            i.features['power'] = 225
            i.features['hitmdef'] = 180
            i.features['speedvigor'] = 119 #+7 Str +7 Spd
            evade = 5
            mblock = 1
            i.features['mblockevade'] = evade | (mblock << 4) #30% evade, 20% mblock
            i.name = "Oborozuki"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True
        if i.name == "Kotetsu":
            i.features['power'] = 245
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 7 #+7 Str
            i.features['magstam'] = 7 #+7 Sta
            evade = 3
            mblock = 0
            i.features['mblockevade'] = evade | (mblock << 4) #30% evade, 20% mblock
            i.features['elements'] = 32  #pearl element
            i.name = "Zanmato"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True
        if i.name == "Forged":
            i.features['power'] = 240
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 64 #+4 Spd
            i.features['magstam'] = 115 #+7 Mag +3 Sta
            evade = 4
            mblock = 4
            i.features['mblockevade'] = evade | (mblock << 4) #30% evade, 20% mblock
            i.name = "SaveTheQueen"

            i.weapon_animation = bytes([30, 30, 32, 0, 55, 0, 164, 0]) #change animation to sword/ragnarok
            i.dataname[1:] = name_to_bytes(i.name, 12)
            i.dataname[0:1] = bytes([217])   #change icon to sword
            convert = True
        if i.name == "Darts":
            i.features['power'] = 215
            i.features['hitmdef'] = 230
            i.features['speedvigor'] = 67 #+3 Str +4 Spd
            i.features['magstam'] = 4 #+4 Sta
            i.name = "Final Trump"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True

        #description is wrong when using Flail
        #if i.name == "Flail":
        #Epee has an empty description. See below for more empty description options
        if i.name == "Epee":
            i.features['power'] = 240
            i.features['hitmdef'] = 150
            i.features['magstam'] = 119 #+7 Mag +7 Sta
            i.name = "Gungnir"

            i.weapon_animation = bytes([93, 93, 43, 5, 51, 0, 168, 0]) #change animation to spear
            i.dataname[1:] = name_to_bytes(i.name, 12)
            i.dataname[0:1] = bytes([218])   #change icon to spear
            convert = True
        if i.name == "Punisher":
            i.features['power'] = 180
            i.features['hitmdef'] = 135
            i.features['magstam'] = 116 #+7 Mag +4 Sta

            #i.features['specialaction'] = 112 #Punisher effect, MP Crit. carried over. 0 this to make it not?
            i.features['breakeffect'] = 19  #0 = Fire, 1 = Ice, etc. Meteor = 19
            i.features["otherproperties"] = 198  #198 is the proc flag, shifted from vanilla            
            i.name = "Stardust Rod"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True

        #description is wrong when Using Full Moon
        #if i.name == "Full Moon":
        #Empty description options:
            #Blossom (wind-elemental)
            #Hardened (dropped by Gigantos)
            #Aura
            #Strato (stronger Bat Pwr than Aura)
            #Davinci Brsh (+1 spd/+1 mag)
            #Kaiser (pearl-elemental)
        if i.name == "DaVinci Brsh":
            i.features['power'] = 170
            i.features['hitmdef'] = 135
            i.features['speedvigor'] = 112 #+7 Spd
            i.features['magstam'] = 112 #+7 Mag

            i.features['breakeffect'] = 30  #0 = Fire, 1 = Ice, etc. Muddle = 30
            i.features["otherproperties"] = 198  #198 is the proc flag, shifted from vanilla
            
            i.name = "Angel Brush"
            i.weapon_animation = bytes([22, 22, 37, 4, 55, 0, 148, 0]) #change animation to brush                                       
            i.dataname[1:] = name_to_bytes(i.name, 12)
            i.dataname[0:1] = bytes([221])   #change icon to brush
            convert = True
        if i.name == "Boomerang":
            i.features['power'] = 225
            i.features['hitmdef'] = 150
            i.features['speedvigor'] = 68 #+4 Str +4 Spd
            i.features['magstam'] = 68 #+4 Mag +4 Sta

            i.features['elements'] = 8   #poison element
            i.features['breakeffect'] = 8  #0 = Fire, 1 = Ice, etc. Bio = 8
            i.features["otherproperties"] = 230  #230 is the proc flag+backrow dmg, shifted from vanilla

            i.weapon_animation = bytes([25, 25, 25, 8, 25, 0, 218, 0]) #change animation to flail
            i.name = "ScorpionTail"
            i.dataname[1:] = name_to_bytes(i.name, 12)
            convert = True

        if convert == True:
            i.unrestrict()
            i.write_stats(fout)
#################end section to convert certain items in FF6A ultimate weapons


#################testing randomize item stats

def manage_items(items: List[ItemBlock], changed_commands: Set[int]=None, itemstats1="n", itemstats2="n",
                 itembreakproc="n", itemteacher="n", itemelemental="n", itemspecial="n", itemfeature="n", itemheavy="n",
                 item_wild_breaks="n", item_extra_effects="n") -> List[ItemBlock]:
    from itemrandomizer import (set_item_changed_commands, extend_item_breaks)

    always_break = Options_.is_code_active('collateraldamage')
    crazy_prices = Options_.is_code_active('madworld')
    extra_effects = Options_.is_code_active('masseffect')
    wild_breaks = Options_.is_code_active('electricboogaloo')
    no_breaks = Options_.is_code_active('nobreaks')
    unbreakable = Options_.is_code_active('unbreakable')

    #set_item_changed_commands(changed_commands)

    ####WC - not sure what these do
    #unhardcode_tintinabar(fout) #<--- this is referenced in read_stats

    ####WC - turn this off as 0x303000 is used by WC menus/objective system
    #extend_item_breaks(fout)   #<--- this is required to get procs set via
    ####
    
    #features["otherproperties"] to work correctly
    #in itemrandomizer.py see break_flags = self.features["breakeffect"] & 0xC0

    auto_equip_relics = []

    
    for i in items:
        
        #WC - add variable to note ultimate weapon item (by checking the item name)
        ultimate_weapon_flag = False
    
        ####Originally: RegalCutlass, Crystal, Stout Spear, Mithril Claw, Kodachi, Kotetsu, Forged, Darts, DaVinci Brsh, Punisher, Epee, Boomerang
        if (i.read_in_name == "Apocalypse" or i.read_in_name == "ZwillXBlade" or 
        i.read_in_name == "Longinus" or i.read_in_name == "Godhand" or
        i.read_in_name == "Oborozuki" or i.read_in_name == "Zanmato" or
        i.read_in_name == "SaveTheQueen" or i.read_in_name == "Final Trump" or
        i.read_in_name == "Gungnir" or i.read_in_name == "Stardust Rod" or
        i.read_in_name == "Angel Brush" or i.read_in_name == "ScorpionTail"):
            ultimate_weapon_flag = True
            #currently not doing anything with this but may be used later

        #WC - don't mutate if ultimate_weapon_flag is True
        if ultimate_weapon_flag == False:
            i.mutate(always_break=always_break, crazy_prices=crazy_prices, extra_effects=extra_effects, wild_breaks=wild_breaks, no_breaks=no_breaks, unbreakable=unbreakable,
                     itemstats1=itemstats1, itemstats2=itemstats2, itembreakproc=itembreakproc, itemteacher=itemteacher, itemelemental=itemelemental,
                     itemspecial=itemspecial, itemfeature=itemfeature, itemheavy=itemheavy,item_wild_breaks=item_wild_breaks, item_extra_effects=item_extra_effects)

        i.unrestrict()   #not sure what this is
        i.write_stats(fout)

        #Gauntlet, Merit Award, Genji Glove:
        if i.features['special2'] & 0x38 and i.is_relic:
            auto_equip_relics.append(i.itemid)

        #write to log
        if i.mutation_log != {}:
            log(str(i.get_mutation_log()), section="item effects")

        #print(i.name + ": " + str(i.price) + " | " + str(i.rank()))

    assert(auto_equip_relics)

    ######CDude:if you don't use this code, the Genji/Merit/Gauntlet flags won't trigger relic-to-gear reequips in the menu if item randomization is in play. 
    if 0 == 1:
        #Test Reequip activation, select menu commands accordingly
        #C3/9EEB:	201091  	JSR $9110      ; Get gear effects
        #C3/9EEE:	20F293  	JSR $93F2      ; Define Y
        #C3/9EF1:	B90000  	LDA $0000,Y    ; Actor
        #C3/9EF4:	C90D    	CMP #$0D       ; Umaro?
        #C3/9EF6:	F007    	BEQ $9EFF      ; Branch if so
        #C3/9EF8:	205C9F  	JSR $9F5C      ; Test Reequip
        #C3/9EFB:	A599    	LDA $99        ; Triggered it?
        #C3/9EFD:	D007    	BNE $9F06      ; Branch if so
        #C3/9EFF:	A904    	LDA #$04       ; C3/1A8A
        #C3/9F01:	8527    	STA $27        ; Queue main menu
        #C3/9F03:	6426    	STZ $26        ; Next: Fade-out
        #C3/9F05:	60      	RTS
        auto_equip_sub = Substitution()
        auto_equip_sub.set_location(0x39EF9)
        auto_equip_sub.bytestring = bytes([0xA0, 0xF1,])
        auto_equip_sub.write(fout)

        #normally unused space. in WC Bank C3, 03FC18-03FFFF are available
        auto_equip_sub.set_location(0x3F1A0)
        auto_equip_sub.bytestring = bytes([0x20, 0xF2, 0x93,
            0xB9, 0x23, 0x00,
            0xC5, 0xB0,
            0xD0, 0x09,
            0xB9, 0x24, 0x00,
            0xC5, 0xB1,
            0xD0, 0x02,
            0x80, 0x4C,
            0x64, 0x99,
            0xA5, 0xB0,
            0x20, 0x21, 0x83,
            0xAE, 0x34, 0x21,
            0xBF, 0x0C, 0x50, 0xD8,
            0x29, 0x38,
            0x85, 0xFE,
            0xA5, 0xB1,
            0x20, 0x21, 0x83,
            0xAE, 0x34, 0x21,
            0xBF, 0x0C, 0x50, 0xD8,
            0x29, 0x38,
            0x04, 0xFE,
            0xB9, 0x23, 0x00,
            0x20, 0x21, 0x83,
            0xAE, 0x34, 0x21,
            0xBF, 0x0C, 0x50, 0xD8,
            0x29, 0x38,
            0x85, 0xFF,
            0xB9, 0x24, 0x00,
            0x20, 0x21, 0x83,
            0xAE, 0x34, 0x21,
            0xBF, 0x0C, 0x50, 0xD8,
            0x29, 0x38,
            0x04, 0xFF,
            0xA5, 0xFE,
            0xC5, 0xFF,
            0xF0, 0x02,
            0xE6, 0x99,
            0x60])
        auto_equip_sub.write(fout)
    ######not sure what this does, comment out for now
    return items

#################testing randomize item stats

#################testing monster appearance
def manage_monster_appearance(monsters: List[MonsterBlock], preserve_graphics: bool = False,
                              monstersprites="n",monsterpalettes="n") -> List[MonsterGraphicBlock]:
    mgs = [m.graphics for m in monsters]
    esperptr = 0x127000 + (5 * 384)
    espers = []
    for j in range(32):
        mg = MonsterGraphicBlock(pointer=esperptr + (5 * j), name="")
        mg.read_data(sourcefile)
        espers.append(mg)
        mgs.append(mg)

    for m in monsters:
        g = m.graphics
        pp = g.palette_pointer
        others = [h for h in mgs if h.palette_pointer == pp + 0x10]
        if others:
            g.palette_data = g.palette_data[:0x10]

        #print(str(m.name) + " | " + str(m.graphicname))

    #input("x")
    nonbosses = [m for m in monsters if not m.is_boss and not m.boss_death]
    bosses = [m for m in monsters if m.is_boss or m.boss_death]
    assert not set(bosses) & set(nonbosses)
    nonbossgraphics = [m.graphics.graphics for m in nonbosses]
    bosses = [m for m in bosses if m.graphics.graphics not in nonbossgraphics]

    for i, m in enumerate(nonbosses):
        if "Chupon" in m.name:
            m.update_pos(6, 6)
            m.update_size(8, 16)
        if "Siegfried" in m.name:
            m.update_pos(8, 8)
            m.update_size(8, 8)
        candidates = nonbosses[i:]
        #print(str(m.name) + " | " + str(m.graphicname))
        
        #all the non-bosses
        #print(m.name + " | " + str(m.miny) + " | " + str(m.maxy) + " | " +
              #str(m.width) + " | " + str(m.height) + " | " +str(m.graphics.graphics) +
              #" | " + str(m.graphics.palette) + " | " + str(m.graphics.palette_pointer) +
              #" | " + str(m.graphics.palette_data) + " | " + str(m.graphics.palette_values) +
              #" | " + str(m.graphics.large))
        #print(m.name + " | " + m.graphicname)
            
        #input("X")

        #WC test
        #this changes the entire monster sprite
        #there are still some issues with sprite placement which causes
        #portions of some large sprites to appear offscreen

        #formations handle the x/y positions
        if monstersprites == "y":
            m.mutate_graphics_swap(candidates)

        #WC - don't change names
        #name = randomize_enemy_name(fout, m.id)
        #m.changed_name = name

    done = {}
    #WC D27820 isn't really "freespace", it's the beginning of the Monster Palettes
    freepointer = 0x127820
    for m in monsters:
        mg = m.graphics

        #WC - don't randomize final boss palette
        # this didn't seem to work, final Kefka palette still got randomized
        #if m.id != 0x12a:
        if 1 == 1:
            #final Kefka
            if m.id == 0x12a and not preserve_graphics:
                idpair = "KEFKA 1"

            #from monsterrandomizer:
            # Dummied Umaro, Dummied Kefka, Colossus, CzarDragon, ???, ???
            #REPLACE_ENEMIES = [0x10f, 0x136, 0x137]
            if m.id in REPLACE_ENEMIES + [0x172]:
                mg.set_palette_pointer(freepointer)
                freepointer += 0x40
                continue
            else:
                #pair each monster with its palette_pointer from mg 
                idpair = (m.name, mg.palette_pointer)

            if idpair not in done:
                #WC - this change the palette of the monster
                if monsterpalettes == "y":
                    mg.mutate_palette()
                #check get_palette_transformer from utils
                #WC - this change the palette of the monster
                    
                done[idpair] = freepointer
                freepointer += len(mg.palette_data)
                mg.write_data(fout, palette_pointer=done[idpair])
            else:
                mg.write_data(fout, palette_pointer=done[idpair],
                              no_palette=True)
        #end of check for final boss

    #WC - Esper palettes change
    if monsterpalettes == "y":
        for mg in espers:
            mg.mutate_palette()
            mg.write_data(fout, palette_pointer=freepointer)
            freepointer += len(mg.palette_data)
    return mgs

########################end monster appearance 

######randomize animations colors
def manage_colorize_animations():
    palettes = []
    #D26000	D26EFF	Battle Animation Palettes (8 colors each)
    for i in range(240):
        pointer = 0x126000 + (i * 16)
        fout.seek(pointer)
        palette = [read_multi(fout, length=2) for _ in range(8)]
        palettes.append(palette)

    for i, palette in enumerate(palettes):
        transformer = get_palette_transformer(basepalette=palette)
        palette = transformer(palette)
        pointer = 0x126000 + (i * 16)
        fout.seek(pointer)
        for c in palette:
            write_multi(fout, c, length=2)
######randomize animations colors

######randomize map palettes
### requires locationformations.txt and locationpaletteswaps.txt
def manage_colorize_dungeons(locations=None, freespaces=None):
    locations = locations or get_locations()
    get_namelocdict()
    paldict = {}
    for l in locations:
        if l.setid in namelocdict:
            name = namelocdict[l.setid]
            if l.name and name != l.name:
                raise Exception("Location name mismatch.")
            if l.name is None:
                l.name = namelocdict[l.setid]
        if l.field_palette not in paldict:
            paldict[l.field_palette] = set([])
        if l.attacks:
            formation = [f for f in get_fsets() if f.setid == l.setid][0]
            if set(formation.formids) != set([0]):
                paldict[l.field_palette].add(l)
        l.write_data(fout)

    from itertools import product
    if freespaces is None:
        freespaces = [FreeBlock(0x271530, 0x271650)]

    done = []
    for line in open(LOCATION_PALETTE_TABLE):
        line = line.strip()
        if line[0] == '#':
            continue
        line = line.split(':')
        if len(line) == 2:
            names, palettes = tuple(line)
            names = names.split(',')
            palettes = palettes.split(',')
            backgrounds = []
        elif len(line) == 3:
            names, palettes, backgrounds = tuple(line)
            names = names.split(',')
            palettes = palettes.split(',')
            backgrounds = backgrounds.split(',')
        elif len(line) == 1:
            names, palettes = [], []
            backgrounds = line[0].split(',')
        else:
            raise Exception("Bad formatting for location palette data.")

        palettes = [int(s, 0x10) for s in palettes]
        backgrounds = [int(s, 0x10) for s in backgrounds]
        candidates = set()
        for name, palette in product(names, palettes):
            if name.endswith('*'):
                name = name.strip('*')
                break
            candidates |= {l for l in locations if l.name == name and l.field_palette == palette and l.attacks}

        if not candidates and not backgrounds:
            palettes, battlebgs = [], []

        battlebgs = {l.battlebg for l in candidates if l.attacks}
        battlebgs |= set(backgrounds)

        transformer = None
        battlebgs = sorted(battlebgs)
        random.shuffle(battlebgs)
        for bg in battlebgs:
            palettenum = battlebg_palettes[bg]
            pointer = 0x270150 + (palettenum * 0x60)
            fout.seek(pointer)
            if pointer in done:
                # raise Exception("Already recolored palette %x" % pointer)
                continue
            raw_palette = [read_multi(fout, length=2) for i in range(0x30)]
            if transformer is None:
                if bg in [0x33, 0x34, 0x35, 0x36]:
                    transformer = get_palette_transformer(always=True)
                else:
                    transformer = get_palette_transformer(basepalette=raw_palette, use_luma=True)
            new_palette = transformer(raw_palette)

            fout.seek(pointer)
            for c in new_palette:
                write_multi(fout, c, length=2)
            done.append(pointer)

        for p in palettes:
            if p in done:
                raise Exception("Already recolored palette %x" % p)
            fout.seek(p)
            raw_palette = [read_multi(fout, length=2) for i in range(0x80)]
            new_palette = transformer(raw_palette)
            fout.seek(p)
            for c in new_palette:
                write_multi(fout, c, length=2)
            done.append(p)

    #if Options_.random_animation_palettes or Options_.swap_sprites or Options_.is_code_active('partyparty'):
    manage_colorize_wor()
    manage_colorize_esper_world()


def manage_colorize_wor():
    transformer = get_palette_transformer(always=True)
    fout.seek(0x12ed00)
    raw_palette = [read_multi(fout, length=2) for i in range(0x80)]
    new_palette = transformer(raw_palette)
    fout.seek(0x12ed00)
    for c in new_palette:
        write_multi(fout, c, length=2)

    fout.seek(0x12ef40)
    raw_palette = [read_multi(fout, length=2) for i in range(0x60)]
    new_palette = transformer(raw_palette)
    fout.seek(0x12ef40)
    for c in new_palette:
        write_multi(fout, c, length=2)

    fout.seek(0x12ef00)
    raw_palette = [read_multi(fout, length=2) for i in range(0x12)]
    airship_transformer = get_palette_transformer(basepalette=raw_palette)
    new_palette = airship_transformer(raw_palette)
    fout.seek(0x12ef00)
    for c in new_palette:
        write_multi(fout, c, length=2)

    for battlebg in [1, 5, 0x29, 0x2F]:
        palettenum = battlebg_palettes[battlebg]
        pointer = 0x270150 + (palettenum * 0x60)
        fout.seek(pointer)
        raw_palette = [read_multi(fout, length=2) for i in range(0x30)]
        new_palette = transformer(raw_palette)
        fout.seek(pointer)
        for c in new_palette:
            write_multi(fout, c, length=2)

    for palette_index in [0x16, 0x2c, 0x2d, 0x29]:
        field_palette = 0x2dc480 + (256 * palette_index)
        fout.seek(field_palette)
        raw_palette = [read_multi(fout, length=2) for i in range(0x80)]
        new_palette = transformer(raw_palette)
        fout.seek(field_palette)
        for c in new_palette:
            write_multi(fout, c, length=2)


def manage_colorize_esper_world():
    loc = get_location(217)
    chosen = random.choice([1, 22, 25, 28, 34, 38, 43])
    loc.palette_index = (loc.palette_index & 0xFFFFC0) | chosen
    loc.write_data(fout)
######randomize map palettes



#################testing randomize monster stats
#######    monsters = manage_monsters()
#######    for m in monsters:
#######     m.write_stats(fout)
def manage_monsters(monsterstats1="n", monsterstats2="n", monstermisc="n", monsterautostatus="n", monsterelemental="n", monsterspecials="n",
                    monsters_darkworld="n", monsterscripts="n", monstercontrol="n", monsterdrops="n", monstersteals="n", monstermorphs="n",
                    vanillacontrol="n", monsterSketchRage="n", vanillaSketchRage="n", easybossupgrades="n") -> List[MonsterBlock]:    
    monsters = get_monsters(sourcefile)
    #safe_solo_terra = not Options_.is_code_active("ancientcave")
    #darkworld = Options_.is_code_active("darkworld")
    change_skillset = None
    #katn = Options_.mode.name == 'katn'
    #final_bosses = (list(range(0x157, 0x160)) + list(range(0x127, 0x12b)) + [0x112, 0x11a, 0x17d])

    #list of bosses
    #Vargas, TunnelArmr, GhostTrain, Dadaluma, Shiva, Ifrit, Number 024, Number 128, Left Crane, Right Crane, Nerapa, Kefka (Narshe), Ultros 1, Ultros 2, Ultros 3, Right Blade, Left Blade, Ipooh, Leader, Piranha, Rizopas, Ultros 4, Air Force
    easy_bosses = [259, 260, 262, 263, 264, 265, 266, 267, 269, 270, 280, 330, 300, 301, 302, 319, 320, 333, 334, 340, 341, 360, 275]

    ranked_items = get_ranked_items()
    exclusion_list = []
    #WC - add variable to note ultimate weapon item (by checking the item name)
    ultimate_weapon_flag = False

    for i in ranked_items:    
        ####Originally: RegalCutlass, Crystal, Stout Spear, Mithril Claw, Kodachi, Kotetsu, Forged, Darts, DaVinci Brsh, Punisher, Epee, Boomerang
        if (i.read_in_name == "Apocalypse" or i.read_in_name == "ZwillXBlade" or 
        i.read_in_name == "Longinus" or i.read_in_name == "Godhand" or
        i.read_in_name == "Oborozuki" or i.read_in_name == "Zanmato" or
        i.read_in_name == "SaveTheQueen" or i.read_in_name == "Final Trump" or
        i.read_in_name == "Gungnir" or i.read_in_name == "Stardust Rod" or
        i.read_in_name == "Angel Brush" or i.read_in_name == "ScorpionTail" or
        i.read_in_name == "Dueling Mask" or i.read_in_name == "Bone Wrist"):
            exclusion_list.append(i.itemid)
            ultimate_weapon_flag = True

        ###### BC on WC week 3
        if (i.name == "Exp. Egg" or i.name == "Fixed Dice" or i.name == "Illumina"
            or i.name == "Paladin Shld" or i.name == "Cursed Shld" or
            i.name == "Ragnarok" or i.name == "ValiantKnife"):
            exclusion_list.append(i.itemid)

    #end of loop through items

    if ultimate_weapon_flag:
        exclusion_list.sort()
        #print(exclusion_list)

    for m in monsters:

        #####WC - good example of a conditional to ignore specific monsters
        #in this example Zone Eater is left untouched
        if "zone eater" in m.name.lower():
            continue
        if not m.name.strip('_') and not m.display_name.strip('_'):
            continue

        if m.id in easy_bosses and easybossupgrades == "y":
            #print(m.display_name)
            m.mutate_easybosses()
            
        #####commenting out boss section
        if 0 == 1:
            if m.id in final_bosses:
                if 0x157 <= m.id < 0x160 or m.id == 0x17d:
                    # deep randomize three tiers, Atma
                    m.randomize_boost_level()
                    if darkworld:
                        m.increase_enemy_difficulty()
                    m.mutate(Options_=Options_, change_skillset=True, safe_solo_terra=False, katn=katn)
                else:
                    m.mutate(Options_=Options_, change_skillset=change_skillset, safe_solo_terra=False, katn=katn)
                if 0x127 <= m.id < 0x12a or m.id == 0x17d or m.id == 0x11a:
                    # boost statues, Atma, final kefka a second time
                    m.randomize_boost_level()
                    if darkworld:
                        m.increase_enemy_difficulty()
                    m.mutate(Options_=Options_, change_skillset=change_skillset, safe_solo_terra=False)
                m.misc1 &= (0xFF ^ 0x4)  # always show name
            else:
                if darkworld:
                    m.increase_enemy_difficulty()
                m.mutate(Options_=Options_, change_skillset=change_skillset, safe_solo_terra=safe_solo_terra, katn=katn)
        #####end of commenting out boss section

        #print("Start: " + str(m.name) + " | " + str(m.controls) + " | " + str(m.sketches) + " | " + str(m.rages))
        #print("Start: " + str(m.id) + " | " + str(m.aiscript))
        #print(m.vanilla_aiscript)
        #print(str(m.name) + " | " + str(m.stats['hp']))
                
        #m.mutate(Options_=Options_, change_skillset=change_skillset, safe_solo_terra=True, katn=False)
        m.mutate(Options_=Options_, change_skillset=True, safe_solo_terra=True, katn=False,
                 monsterstats1=monsterstats1, monsterstats2=monsterstats2, monstermisc=monstermisc, monsterautostatus=monsterautostatus,
                 monsterelemental=monsterelemental, monsterspecials=monsterspecials, monsters_darkworld=monsters_darkworld,
                 monsterscripts=monsterscripts, monstercontrol=monstercontrol, monsterdrops=monsterdrops,
                 monstersteals=monstersteals, monstermorphs=monstermorphs, vanillacontrol=vanillacontrol, monsterSketchRage=monsterSketchRage,
                 vanillaSketchRage=vanillaSketchRage)

        #print("End: " + str(m.name) + " | " + str(m.aiscript))
        #print(m.name + " | " + str(m.statuses) + " | " + str(m.immunities) + " | " +
              #str(m.absorb) + " | " + str(m.null) + " | " + str(m.weakness))

        #m.statuses[3] |= 0x01  #give all enemies trueknight
        #m.statuses[3] |= 0x02  #give all enemies runic
        #m.statuses[3] |= 0x04 #give all enemies Life3

        #mutate_items is never called in mutate
        m.mutate_items(katnFlag=False,monsterdrops=monsterdrops,monstersteals=monstersteals,
                       exclusion_list=exclusion_list)
        
        if monstermorphs == "y":
            m.mutate_metamorph()

        if monsterspecials == "y":
            #this changes the name/animation of the special attack
            #but the actual effect appears to be the same unless otherwise
            #changed in earlier mutate()
            m.randomize_special_effect(fout)

        #print(str(m.name) + ": " + str(m.special))

        m.write_stats(fout)
        
        #not sure about these, ignore them for now
        #m.tweak_fanatics()     #adjusts L. magics and Magimaster, no need
        #m.relevel_specifics()  #adjusts monster ID's 0x4F, 0xBD, 0xAD: Bomb, SoulDancer, Outsider

    #WC - does this actually need to happen. comment out for now
    #change_enemy_name(fout, 0x166, "L.255Magic")

    #WC - probably don't need to do this since WC already moves stuff around if the player wants it to
    #shuffle_monsters(monsters, safe_solo_terra=True)
            
    return monsters

#################testing randomize monster stats


####################testing equip anything
def manage_equip_anything():
    equip_anything_sub = Substitution()
    equip_anything_sub.set_location(0x39b8b)
    equip_anything_sub.bytestring = bytes([0x80, 0x04])
    equip_anything_sub.write(fout)
    equip_anything_sub.set_location(0x39b99)
    equip_anything_sub.bytestring = bytes([0xEA, 0xEA])
    equip_anything_sub.write(fout)

#################testing randomize formations


######################testing command modifcations
def commands_from_table(tablefile: str) -> List:
    commands = []
    for i, line in enumerate(open(tablefile)):
        line = line.strip()
        if line[0] == '#':
            continue

        while '  ' in line:
            line = line.replace('  ', ' ')
        c = CommandBlock(*line.split(','))
        c.set_id(i)
        commands.append(c)
    return commands


#########randomize command/magic/item slots. leaves Fight command, forces Fight command
#########on Gau as well. 20% of Magitek not allowed.
def manage_commands(commands: Dict[str, CommandBlock],
                    command_no_guarantee_itemmagic="n", command_more_duplicates="n"):
    """
    Takes in a dict of commands and randomizes them.

    Parameters
    ----------
    commands: a dictionary with the 30 default commands as
    string keys and CommandBlock values, e.g.:
    {'fight': <skillrandomizer.CommandBlock object at 0x0000020D06918760>,
     'item': <skillrandomizer.CommandBlock object at 0x0000020D06918640>,
     'magic': <skillrandomizer.CommandBlock object at 0x0000020D069188B0>,
     'morph': <skillrandomizer.CommandBlock object at 0x0000020D069188E0>,
     ...
     'possess': <skillrandomizer.CommandBlock object at 0x0000020D06918D60>, 
     'magitek': <skillrandomizer.CommandBlock object at 0x0000020D06918D90>}
    """
    characters = get_characters()

    #invalid_commands = ["fight", "item", "magic", "xmagic",
                        #"def", "row", "summon", "revert"]

    #WC - don't care about xmagic appearing multiple times
    invalid_commands = ["fight", "item", "magic", 
                        "def", "row", "summon", "revert"]

    #WC - 100% chance to call magitek an invalid command to randomize
    #if random.randint(1, 5) != 5:
    if 1 == 1:
        invalid_commands.append("magitek")
        invalid_commands.append("possess")
        invalid_commands.append("shock")
        invalid_commands.append("control")

    if not Options_.replace_commands:
        invalid_commands.extend(FORBIDDEN_COMMANDS)

    invalid_commands = {c for c in commands.values() if c.name in invalid_commands}

    def populate_unused():
        unused_commands = set(commands.values())
        unused_commands = unused_commands - invalid_commands
        return sorted(unused_commands, key=lambda c: c.name)

    unused = populate_unused()
    xmagic_taken = False
    random.shuffle(characters)

    for c in characters:
        #WC - don't fix Gau
        #commenting this out doesn't seem to do anything anyways. Fight is always first
        #if c.id == 11:
            # Fixing Gau
            #c.set_battle_command(0, commands["fight"])

        if Options_.is_code_active('metronome'):
            c.set_battle_command(0, command_id=0)
            c.set_battle_command(1, command_id=0x1D)
            c.set_battle_command(2, command_id=2)
            c.set_battle_command(3, command_id=1)
            c.write_battle_commands(fout)
            continue

        if Options_.is_code_active('collateraldamage'):
            c.set_battle_command(1, command_id=0xFF)
            c.set_battle_command(2, command_id=0xFF)
            c.set_battle_command(3, command_id=1)
            c.write_battle_commands(fout)
            continue

        #for all non-Gogo/Umaro characters:
        if c.id <= 11:
            using = []

            #WC - guarantee Magic, Item
            if command_no_guarantee_itemmagic == "n":
                using.append(commands["item"])
                using.append(commands["magic"])
            else:
            ####WC - 50% chance of item, 50% chance of magic
                while not using:
                    #50% chance of item being in the guaranteed list of commands
                    #if random.randint(0, 1):
                    #2/3 chance of item being in the guaranteed list of commands
                    #guarantee Gau can use items
                    if random.randint(1, 3) > 1 or c.id == 11:
                        using.append(commands["item"])

                    #50% chance of magic being in the guaranteed list of commands
                    if random.randint(0, 1):
                        using.append(commands["magic"])

                        #WC - instead of BC where xmagic is only allowed one time,
                        #remove xmagic from the invalid commands list
                        #if not xmagic_taken:
                            #using.append(commands["xmagic"])
                            #xmagic_taken = True
                        #else:
                            #using.append(commands["magic"])

            #print(c.name)
            #loops up to 3 times
            #to minimize duplicates, unused commands is carried over
            #for each character
            while len(using) < 3:
                unused_commands = ""

                #pulls in unused commands for possible options, if all the unused
                #commands are used, repopulate them anew - this will lead to
                #duplicate commands
                if not unused:
                    unused = populate_unused()
                    #print(unused)

                for i, command in enumerate(unused):
                    unused_commands = unused_commands + ", " + str(command.name)
                    #input("unused")

                #print(unused_commands)
                com = random.choice(unused)

                ####WC - unique command assignment. comment out to make unique command
                if command_more_duplicates == "n":
                    unused.remove(com)

                ####WC - unique command assignment. swap comment to make unique command
                #if 1 == 1:
                #if command_more_duplicates == "y":
                    #pass
                #if command_more_duplicates == "n":
                if com not in using:
                    using.append(com)
                    if com.name == "morph":
                        invalid_commands.add(com)
                        morph_char_sub = Substitution()
                        morph_char_sub.bytestring = bytes([0xC9, c.id])
                        morph_char_sub.set_location(0x25E32)
                        morph_char_sub.write(fout)

            #50% chance to remove the fight command
            if 0 == 1 and command_more_duplicates == "y":
                if random.randint(0, 1):
                    check_morph = random.choice(unused)
                    if check_morph.name != "morph":
                        c.set_battle_command(0, check_morph)
                    else:
                        c.set_battle_command(0, commands["fight"])

            #print(using)
            
            #for i, command in enumerate(reversed(using)):
                #print(command.name)
            #input(c.name)
            
            for i, command in enumerate(reversed(using)):
                #print(command.name)
                c.set_battle_command(i + 1, command=command)
                if i >= 4:
                    print("too many commands")

            ####WC - Carry over Gau's lack of fight command
            if c.id == 11:
                com = random.choice(unused)
                while com.name == "capture":
                    com = random.choice(unused)
                forceCapture = True
                if forceCapture:
                    c.set_battle_command(0, command_id=6)
                else:
                    c.set_battle_command(0, com)
                    if command_more_duplicates == "n":
                        unused.remove(com)

        #Gogo and Umaro
        else:
            c.set_battle_command(1, command_id=0xFF)
            c.set_battle_command(2, command_id=0xFF)
        c.write_battle_commands(fout)

    magitek_skills = [SpellBlock(i, sourcefile) for i in range(0x83, 0x8B)]
    for ms in magitek_skills:
        ms.fix_reflect(fout)

    return commands
######################testing command modifcations



def write_all_locations_misc():
    #write_all_chests()
    #write_all_npcs()
    #write_all_events()
    write_all_entrances()


def write_all_chests():
    locations = get_locations()
    locations = sorted(locations, key=lambda l: l.locid)

    nextpointer = 0x2d8634
    for l in locations:
        nextpointer = l.write_chests(fout, nextpointer=nextpointer)


def write_all_npcs():
    locations = get_locations()
    locations = sorted(locations, key=lambda l: l.locid)

    nextpointer = 0x41d52
    for l in locations:
        if hasattr(l, "restrank"):
            nextpointer = l.write_npcs(fout, nextpointer=nextpointer,
                                       ignore_order=True)
        else:
            nextpointer = l.write_npcs(fout, nextpointer=nextpointer)


def write_all_events():
    locations = get_locations()
    locations = sorted(locations, key=lambda l: l.locid)

    nextpointer = 0x40342
    for l in locations:
        nextpointer = l.write_events(fout, nextpointer=nextpointer)

#overworld location randomization
def randomizeWorldEntrances(e, destArray, locToReplace, targetArea, passThru):
    #e is an entrance set

    def listToString(s): 
        
        # initialize an empty string
        str1 = "" 
        firstPass = 0
        # traverse in the string  
        for ele in s:
            if firstPass == 0:
                str1 = str(ele)
                firstPass = 1
            else:
                str1 = str1 + ", " + str(ele)
        
        # return string  
        return str1 
    #end listToString converter

    log(targetArea + " Entrance Randomizer",section=None)
    log("Original DestID, Original DestX, Original DestY, Original Destination Name -> New DestID, New DestX, New DestY, New Destination Name",section=None)

    locCounter = 0
    nextlocIndex = 0

    #loop through 0 to entrances
    for locCounter in range(len(e.entrances)):

        if targetArea == "0 World of Balance":
            #do not modify these entrance destinations, there are issues with them
            #if locCounter == 5 or locCounter == 11 or locCounter == 12 or locCounter == 13 or locCounter == 15 or locCounter == 18 or locCounter == 19 or locCounter == 20 or locCounter == 39 or locCounter == 40:

            #5: cave to SF
            #11, 12: Mt Koltz
            #18, 19, 20: Phantom Forest
            #39, 40: Imperial Base
            #41: Cave to the Sealed Gate

            #added locCounter <4 and ==41 to prevent Chocobo Stables and Cave to Sealed Gate. removed locCounter == 13 (Returners) and ==15 (Baren Falls)
            if locCounter < 4 or locCounter == 5 or locCounter == 11 or locCounter == 12 or \
               locCounter == 18 or locCounter == 19 or locCounter == 20 or locCounter == 39 or \
               locCounter == 40 or locCounter == 41:
                actualCounter = locCounter
                
            else:
                actualCounter = locCounter
                                                
                #if locCounter is equal to a locToReplace index, pick a new destination
                if actualCounter == locToReplace[nextlocIndex]:
                    picked = random.choice(destArray)
                    destArray.remove(picked)

                    nextlocIndex = nextlocIndex+1   #set the next destination

                #write to spoiler log which entrances have changed
                original_dest = e.entrances[actualCounter].dest
                original_destination = e.entrances[actualCounter].destination
                original_destx = e.entrances[actualCounter].destx
                original_desty = e.entrances[actualCounter].desty
                original_entx = e.entrances[actualCounter].x
                original_enty = e.entrances[actualCounter].y
                #clean-up string for output to spoiler log
                if str(original_destination) == "5d":
                    original_destination = "5d Sabin's House"
                if str(original_destination) == "6c":
                    original_destination = "6c Returners"
                if str(original_destination) == "132 Tzen--World of Ruin, postdestruction":
                    original_destination = "132 Tzen (World of Balance)"
                if str(original_destination) == "ed":
                    original_destination = "ed Opera House"
                if str(original_destination) == "177 Cave near Thamasa, Esper room":
                    original_destination = "177 Esper Mountain near Thamasa"

                log(str(original_dest) + ", " + str(original_destx) + ", " + str(original_desty) + ", " + str(original_destination) + " -> " + listToString(picked),section=None)

                #change the entrance destination in question to the destination picked from the array
                e.entrances[actualCounter].dest = picked[0]
                e.entrances[actualCounter].destx = picked[1]
                e.entrances[actualCounter].desty = picked[2]

                #store Returner's destination
                if e.entrances[actualCounter].dest == 620:
                    passThru[0] = original_dest
                    passThru[1] = original_entx
                    passThru[2] = original_enty
                    #print(passThru)

                #store Baren's destination
                if e.entrances[actualCounter].dest == 166:
                    passThru[3] = original_dest
                    passThru[4] = original_entx
                    passThru[5] = original_enty
                    #print(passThru)
                    
        elif targetArea == "1 World of Ruin":   #world of ruin
            #do not modify these entrance destinations, there are issues with them

            #8: darill's tomb
            #12: cave to Fig Castle
            #31 (33 in Excel sheet): Hidon cave
            if locCounter == 8 or locCounter == 12 or locCounter == 31:
                actualCounter = locCounter
            else:
                actualCounter = locCounter
                                                
                #if locCounter is equal to a locToReplace index, pick a new destination
                if actualCounter == locToReplace[nextlocIndex]:
                    picked = random.choice(destArray)
                    destArray.remove(picked)

                    nextlocIndex = nextlocIndex+1

                #write to spoiler log which entrances have changed
                original_dest = e.entrances[actualCounter].dest
                original_destination = e.entrances[actualCounter].destination
                original_destx = e.entrances[actualCounter].destx
                original_desty = e.entrances[actualCounter].desty
                #clean-up string for output to spoiler log
                if str(original_destination) == "11d Doma (after liberation?)":
                    original_destination = "11d Doma"
                if str(original_destination) == "131 Tzen--World of Ruin, predestruction":
                    original_destination = "131 Tzen (World of Ruin)"
                if str(original_destination) == "ed":
                    original_destination = "ed Opera House"
                if str(original_destination) == "a9 Nikeah--World of Balance":
                    original_destination = "a9 Nikeah (World of Ruin)"
                if str(original_destination) == "11c Maranda--World of Balance":
                    original_destination = "11c Maranda (World of Ruin)"
                if str(original_destination) == "c6 Jidoor--World of Balance":
                    original_destination = "c6 Jidoor (World of Ruin)"
                log(str(original_dest) + ", " + str(original_destx) + ", " + str(original_desty) + ", " + str(original_destination) + " -> " + listToString(picked),section=None)

                #change the entrance destination in question to the destination picked from the array
                e.entrances[actualCounter].dest = picked[0]
                e.entrances[actualCounter].destx = picked[1]
                e.entrances[actualCounter].desty = picked[2]
        else:
            actualCounter = locCounter
                                            
            #if locCounter is equal to a locToReplace index, pick a new destination
            if actualCounter == locToReplace[nextlocIndex]:
                picked = random.choice(destArray)
                destArray.remove(picked)

                nextlocIndex = nextlocIndex+1

                #write to spoiler log which entrances have changed
                original_dest = e.entrances[actualCounter].dest
                original_destination = e.entrances[actualCounter].destination
                original_destx = e.entrances[actualCounter].destx
                original_desty = e.entrances[actualCounter].desty
                log(str(original_dest) + ", " + str(original_destx) + ", " + str(original_desty) + ", " + str(original_destination) + " -> " + listToString(picked),section=None)

                #change the entrance destination in question to the destination picked from the array
                e.entrances[actualCounter].dest = picked[0]
                e.entrances[actualCounter].destx = picked[1]
                e.entrances[actualCounter].desty = picked[2]
                
        #end of check for world
            
    #next entrance
    return e

#end of randomizeWorldEntrances

#this controls the randomization of locations
def write_all_entrances():
    entrancesets = [l.entrance_set for l in get_locations()]
    entrancesets = entrancesets[:0x19F]
    nextpointer = 0x1FBB00 + (len(entrancesets) * 2) + 2
    longnextpointer = 0x2DF480 + (len(entrancesets) * 2) + 2
    total = 0

    #########testing functions
    #input("write_all_entrances")
    #print(entrancesets)
    #entrancesets are a bunch of EntranceSet objects: each object is a location with entrance X/Y locations and destinations

    ####run this to view all entrance destinations
    #for e in entrancesets:
        #for a, value in enumerate(e.entrances):
            #print(str(value.location) + " | " + str(value.entid) + " | " + str(value.x) + " | " + str(value.y) + " | " + str(value.dest) + " | " + str(value.destination) + " | " + str(value.destx) + " | " + str(value.desty))

    ####run this to view all long (multi-tile) entrances
    #for e in entrancesets:
        #for a, value in enumerate(e.longentrances):
            #print(str(value.location) + " | " + str(value.entid) + " | " + str(value.x) + " | " + str(value.y) + " | " + str(value.width) + " | " + str(value.dest) + " | " + str(value.destination) + " | " + str(value.destx) + " | " + str(value.desty))

    #WoB_R flips to 1 after WoB entrances are randomized
    WoB_R = 0
    WoR_R = 0
    WoB_Narshe = 0
    WoB_name = "0 World of Balance"
    WoR_name = "1 World of Ruin"
    WoB_Narshe_name = "14 Narshe (WoB) (normal)"
    passThru = [0,0,0,0,0,0]
    
    #loop through all entrancesets in the game
    for e in entrancesets:
        total += len(e.entrances)

        #randomize world map entrances to specific destinations
        for a, value in enumerate(e.entrances):

            ####block out for testing purposes
            #upon finding the first World of Balance entrance
            if 1 == 1:
                if str(value.location) == WoB_name:

                    if WoB_R == 0:                    
                        #destArray = [[2574, 8, 12, "Chocobo Stable"], [2580, 38, 61, "Narshe (WoB)"], [6731, 1, 28, "SF (WoB)"], [605, 7, 14, "Sabin's House"], [620, 11, 55, "Returners"], 
                                     #[627, 7, 13, "Gau Manor"], [6825, 1, 35, "Nikeah"], [679, 12, 25, "Mt. Crescent"], [2748, 23, 29, "Koh"], [2717, 18, 40, "Mobliz"],
                                     #[697, 7, 13, "Coliseum Guy House"], [2758, 15, 61, "Jidoor"], [2844, 11, 29, "Maranda"], [2866, 23, 29, "Tzen"], [6979, 2, 17, "Albrook"],
                                     #[15069, 61, 44, "Zozo"], [2797, 60, 51, "Opera House"], [2942, 25, 37, "Cave to Sealed Gate"], [887, 55, 31, "Esper Mtn"]]
                        #locToReplace = [0, 4, 6, 10, 13, 14, 16, 21, 22, 24, 25, 26, 29, 31, 33, 35, 38, 41, 42]
                        #remove chocobo stable and cave to sealed gate for character gating

                        #added Returners (13), Baren Falls (15)
                        destArray = [[2580, 38, 61, 84, 34, "Narshe (WoB)"], [6731, 1, 28, "SF (WoB)"], [605, 7, 14, "Sabin's House"], [620, 11, 55, "Returners"], 
                                     [627, 7, 13, "Gau Manor"], [166, 9, 13, "Baren Falls"], [6825, 1, 35, "Nikeah"], [679, 12, 25, "Mt. Crescent"], [2748, 23, 29, "Koh"],
                                     [2717, 18, 40, "Mobliz"],
                                     [697, 7, 13, "Coliseum Guy House"], [2758, 15, 61, "Jidoor"], [2844, 11, 29, "Maranda"], [2866, 23, 29, "Tzen"], [6979, 2, 17, "Albrook"],
                                     [15069, 61, 44, "Zozo"], [2797, 60, 51, "Opera House"], [887, 55, 31, "Esper Mtn"]]
                        locToReplace = [4, 6, 10, 13, 14, 15, 16, 21, 22, 24, 25, 26, 29, 31, 33, 35, 38, 42]
                        
                        targetArea = "0 World of Balance"
                        
                        randomizeWorldEntrances(e, destArray, locToReplace, WoB_name, passThru)
                        WoB_R = 1
                        #runs once for WoB

                if str(value.location) == WoR_name:

                    if WoR_R == 0:                    
                        destArray = [[2576, 8, 12, "Chocobo Stable"], [908, 8, 12, "Cid's House"], [6980, 2, 17, "Albrook"],
                                     [2865, 23, 29, "Tzen"], [15006, 31, 18, "Mobliz"], [6825, 1, 35, "Nikeah"], [2973, 23, 15, "Colloseum"],
                                     [6730, 1, 28, "SF"], [2749, 23, 29, "Koh"], [2913, 33, 61, "Veldt Cave"], [2797, 60, 51, "Opera"],
                                     [2844, 11, 29, "Maranda"], [2592, 38, 61, "Narshe"], [643, 7, 13, "Gau Manor"], [874, 8, 13, "Fanatic's"],
                                     [15069, 61, 44, "Zozo"], [2758, 15, 61, "Jidoor"], [2904, 23, 46, "Thamasa"], [2845, 33, 61, "Doma"],
                                     [639, 7, 13, "Duncan"]]
                        locToReplace = [0, 3, 4, 6, 7, 9, 11, 13, 14, 16, 17, 18, 20, 21, 22, 23, 26, 28, 29, 32]
                        targetArea = "1 World of Ruin"
                        
                        randomizeWorldEntrances(e, destArray, locToReplace, WoR_name, passThru)
                        WoR_R = 1

                        #runs once for WoR

            ####block out for testing purposes

            #try SF Cave WoB entrance rando
            #if str(value.location) == "0 World of Balance":
                #change the entrance destination in question to the destination picked from the array
                #e.entrances[4].dest = 620
                #e.entrances[4].destx = 11
                #e.entrances[4].desty = 55

                #narshe was picked as entrance for SF Cave WoB
                #SF Cave WoB

        #end of loop through all the non-long entrances in an entranceset
    #end of loop through all non-long entrances in the game
                        
    #use this section to handle long entrances for Returners and Baren Falls
    Returners_set = 0
    Baren_set = 0        

    for e in entrancesets:
        total += len(e.entrances)
        
        for a, value in enumerate(e.longentrances):
            if str(value.location) == "6c" and Returners_set == 0:
                e.longentrances[1].dest = 8192
                e.longentrances[1].destx = passThru[1]
                e.longentrances[1].desty = passThru[2]
                Returners_set = 1

            if str(value.location) == "a6 Baren Falls--Entrance" and Baren_set == 0:
                e.longentrances[0].dest = 8192
                e.longentrances[0].destx = passThru[4]
                e.longentrances[0].desty = passThru[5]
                Baren_set = 1

        #end of loop through all the long entrances in an entranceset
    #end of loop through all long entrances in the game

            #try Narshe map rando
            #if str(value.location) == "14 Narshe (WoB) (normal) ":
                #if WoB_Narshe == 0:                    
                    #destArray = [[2076, 8, 45, "Narshe Inn"], [30, 79, 17, "Narshe Treasure Room"], [2072, 25, 13, "Narshe Weapon"], [2075, 64, 13, "Narshe Relic"], [2078, 110, 25, "Narshe Elder House"], [30, 80, 35, "Narshe Cursed Shld House"], [2074, 44, 13, "Narshe Item"], [2073, 6, 14, "Narshe Armor Left"], [2073, 11, 11, "Narshe Armor Right"], [30, 55, 34, "Narshe Arvis House Left"], [2152, 108, 52, "Narshe School"]]
                    #locToReplace = [0, 1,2,3,4,5,6,7,8,9,15]
                    #randomizeWorldEntrances(e, destArray, locToReplace, WoB_Narshe_name)
                    #WoB_Narshe = 1


            ####generic code for replacing a single entrance
            #targetArea = "0 World of Balance"
            #targetEnt = 42
            #targetEntX = 229
            #targetEntY = 130
            #targetWidth = 191 <- only use this for longentrances

            #targetDest = 2580
            #targetDestX = 38
            #targetDestY = 61

            #for a, value in enumerate(e.entrances):
                #if str(value.location) == targetArea and value.entid == targetEnt and value.x == targetEntX and value.y == targetEntY:
                    #if targetArea == "1 World of Ruin" and value.entid > 20:
                        #e.entrances[value.entid-2].dest = targetDest
                        #e.entrances[value.entid-2].destx = targetDestX
                        #e.entrances[value.entid-2].desty = targetDestY
                        #input("destination written")                    
                    #else:
                        #e.entrances[value.entid].dest = targetDest
                        #e.entrances[value.entid].destx = targetDestX
                        #e.entrances[value.entid].desty = targetDestY 
                        #input("destination  written")

            #use this code if the entrance is a longentrance
            #for a, value in enumerate(e.longentrances):
                #if str(value.location) == targetArea and value.entid == targetEnt and value.x == targetEntX and value.y == targetEntY:
                    #e.longentrances[value.entid].dest = targetDest
                    #e.longentrances[value.entid].destx = targetDestX
                    #e.longentrances[value.entid].desty = targetDestY                    
        

        ####more testingfunctions
        #print(e.pointer)
        #print(e.longpointer)
        #print(e.entrances)      #all the exits in the location
        #print(e.longentrances)  #multi-tile exits e.g. for towns with borders
        #print("entid" + str(e.entid))
        #print("entrances:")
        #print(e.entrances)

        #this does the actual write back to the ROM
        nextpointer, longnextpointer = e.write_data(fout, nextpointer,
                                                    longnextpointer)



    fout.seek(e.pointer + 2)
    write_multi(fout, (nextpointer - 0x1fbb00), length=2)
    fout.seek(e.longpointer + 2)
    write_multi(fout, (longnextpointer - 0x2df480), length=2)


def get_namelocdict():
    if namelocdict:
        return namelocdict

    for line in open(LOCATION_TABLE):
        line = line.strip().split(',')
        name, encounters = line[0], line[1:]
        encounters = list(map(hex2int, encounters))
        namelocdict[name] = encounters
        for encounter in encounters:
            assert encounter not in namelocdict
            namelocdict[encounter] = name

    return namelocdict


def dummy_item(item):
    dummied = False
    for m in get_monsters():
        dummied = m.dummy_item(item) or dummied

    for mm in get_metamorphs(sourcefile):
        dummied = mm.dummy_item(item) or dummied

    for l in get_locations():
        dummied = l.dummy_item(item) or dummied

    return dummied

def randomize(args):
    global outfile, sourcefile, flags, seed, fout, ALWAYS_REPLACE, NEVER_REPLACE

#test is off so ignore this
    if TEST_ON:
        while len(args) < 3:
            args.append(None)
        args[1] = TEST_FILE
        args[2] = TEST_SEED
    sleep(0.5)
    #print('You are using Beyond Chaos EX randomizer version "%s".' % VERSION)
    print('You are using a Beyond Chaos mod for FF6 Worlds Collide + Entrance Randomizer. Stability is not guaranteed.')
    if BETA:
        print("WARNING: This version is a beta! Things may not work correctly.")

#get the location of the ROM
    previous_rom_path = ''
    if len(args) > 2:
        sourcefile = args[1].strip()
    else:
        try:
            config = configparser.ConfigParser()
            config.read('bcex.cfg')
            if 'ROM' in config:
                previous_rom_path = config['ROM']['Path']
        except IOError:
            pass

        previous = f" (blank for previous: {previous_rom_path})" if previous_rom_path else ""
        sourcefile = input(f"Please input the file name of your copy of "
                           f"your FF6 WC rom{previous}:\n> ").strip()
        print()


#section for error checking ROM
    if previous_rom_path and not sourcefile:
        sourcefile = previous_rom_path
    try:
        f = open(sourcefile, 'rb')
        data = f.read()
        f.close()
    except IOError:
        response = input(
            "File not found. Would you like to search the current directory \n"
            "for a valid FF3 1.0 rom? (y/n) ")
        if response and response[0].lower() == 'y':
            for filename in sorted(os.listdir('.')):
                stats = os.stat(filename)
                size = stats.st_size
                if size not in [3145728, 3145728 + 0x200]:
                    continue

                try:
                    f = open(filename, 'r+b')
                except IOError:
                    continue

                data = f.read()
                f.close()
                if size == 3145728 + 0x200:
                    data = data[0x200:]
                h = md5(data).hexdigest()
                if h == MD5HASH:
                    sourcefile = filename
                    break
            else:
                raise Exception("File not found.")
        else:
            raise Exception("File not found.")
        print("Success! Using valid rom file: %s\n" % sourcefile)
    del f
#end section for error checking ROM

#flag saving    
    saveflags = False
    if sourcefile != previous_rom_path:
        saveflags = True

    flaghelptext = '''0-9 Shorthand for the text saved under that digit, if any
!   Recommended new player flags
-   Use all flags EXCEPT the ones listed'''

    speeddial_opts = {}

#seed input
    if len(args) > 2:
        fullseed = args[2].strip()
    else:
        #for WC, don't waste time with seed values
        #fullseed = input("Please input a seed value (blank for a random "
                         #"seed):\n> ").strip()
        fullseed = "" #<- add this to make testing faster
        print()

        if '.' not in fullseed:
            config = configparser.ConfigParser()
            config.read('bcex.cfg')
            if 'speeddial' in config:
                speeddial_opts = config['speeddial']
            else:
                try:
                    savedflags = []
                    with open('savedflags.txt', 'r') as sff:
                        savedflags = [l.strip() for l in sff.readlines() if ":" in l]
                    for line in savedflags:
                        line = line.split(':')
                        line[0] = ''.join(c for c in line[0] if c in '0123456789')
                        speeddial_opts[line[0]] = ''.join(line[1:]).strip()
                except IOError:
                    pass

            speeddial_opts['!'] = '-dfklu partyparty makeover johnnydmad'


#section to handle game mode. 'ancientcave' modes implement location randomization
#so we default mode_str to be 4
            mode_num = None
            while mode_num not in range(len(ALL_MODES)):
                #print("Available modes:\n")
                #for i, mode in enumerate(ALL_MODES):
                    #print("{}. {} - {}".format(i+1, mode.name, mode.description))

                #mode_str = input("\nEnter desired mode number or name:\n").strip()
                mode_str = 4
                try:
                    mode_num = int(mode_str) - 1
                except ValueError:
                    for i, m in enumerate(ALL_MODES):
                        if m.name == mode_str:
                            mode_num = i
                            break
            mode = ALL_MODES[mode_num]
            allowed_flags = [f for f in ALL_FLAGS if f.name not in mode.prohibited_flags]
            print()

#added
#always add sprint shoes flag and nothing else
            flags = "z"

            fullseed = ".%i.%s.%s" % (mode_num+1, flags, fullseed)
            print()


#flags now set. validate flags and ROM name

    try:
        version, mode_str, flags, seed = tuple(fullseed.split('.'))
    except ValueError:
        raise ValueError('Seed should be in the format <version>.<mode>.<flags>.<seed>')
    mode_str = mode_str.strip()
    mode_num = None
    try:
        mode_num = int(mode_str) - 1
    except ValueError:
        for i, m in enumerate(ALL_MODES):
            if m.name == mode_str:
                mode_num = i
                break

    if mode_num not in range(len(ALL_MODES)):
        raise Exception("Invalid mode specified")
    Options_.mode = ALL_MODES[mode_num]
    allowed_flags = [f for f in ALL_FLAGS if f.name not in Options_.mode.prohibited_flags]

    seed = seed.strip()
    if not seed:
        seed = int(time())
    else:
        seed = int(seed)
    seed = seed % (10**10)
    reseed()

    if saveflags:
        try:
            config = configparser.ConfigParser()
            config.read('bcex.cfg')
            if 'ROM' not in config:
                config['ROM'] = {}
            if 'speeddial' not in config:
                config['speeddial'] = {}
            config['ROM']['Path'] = sourcefile
            config['speeddial'].update({k:v for k, v in speeddial_opts.items() if k != '!'})
            with open('bcex.cfg', 'w') as cfg_file:
                config.write(cfg_file)
        except:
            print("Couldn't save flag string\n")
        else:
            try:
                os.remove('savedflags.txt')
            except OSError:
                pass

    if '.' in sourcefile:
        tempname = sourcefile.rsplit('.', 1)
    else:
        tempname = [sourcefile, 'smc']
    outfile = '.'.join([tempname[0], str(seed), tempname[1]])
    outlog = '.'.join([tempname[0], str(seed), 'txt'])

    if len(data) % 0x400 == 0x200:
        print("NOTICE: Headered ROM detected. Output file will have no header.")
        data = data[0x200:]
        sourcefile = '.'.join([tempname[0], "unheadered", tempname[1]])
        f = open(sourcefile, 'w+b')
        f.write(data)
        f.close()


    h = md5(data).hexdigest()
#md5 check. will fail against WC seed. ignore it anyways
    if 1 == 0:
        if h != MD5HASH:
            print("WARNING! The md5 hash of this file does not match the known "
                  "hash of the english FF6 1.0 rom!")
            x = input("Continue? y/n ")
            if not (x and x.lower()[0] == 'y'):
                return

#make a copy of the ROM
    copyfile(sourcefile, outfile)

    flags = flags.lower()
    flags = flags.replace('endless9', 'endless~nine~')
    for d in "!0123456789":
        if d in speeddial_opts:
            replacement = speeddial_opts[d]
        else:
            replacement = ''
        flags = flags.replace(d, replacement)
        flags = flags.replace('endless9', 'endless~nine~')
    flags = flags.replace('endless~nine~', 'endless9')

    if version and version != VERSION:
        print("WARNING! Version mismatch! "
              "This seed will not produce the expected result!")
    #s = "Using seed: %s.%s.%s.%s" % (VERSION, options_.mode.name, flags, seed)
    #print(s)
    #log(s, section=None)
    log("\n\nThis is a spoiler log for a Beyond Chaos mod for FF6 Worlds Collide + Entrance Randomizer.",
        section=None)
    log("For more information, visit the FF6 Worlds Collide discord: https://discord.gg/5MPeng5",
        section=None)


#outfile is opened to be written to
    fout = open(outfile, "r+b")

#does ROM need to be expanded if location randomization?
    #expand_rom()

    #commands = commands_from_table(COMMAND_TABLE)
    #commands = {c.name:c for c in commands}

#related to commands
    
    #preserve_graphics = (not Options_.swap_sprites and
                         #not Options_.is_code_active('partyparty'))

    #required ROM read-in

    #testval = '\r'
    #print(ord(testval))  #-> 13
    #print(hex(ord(testval)))  #-> 0xd
    #print(testval)  #-> nothing shows up, carriage return CR
    #input("X")

    monsters = get_monsters(sourcefile)
    formations = get_formations(sourcefile)
    #get_formations calls formationrandomizer lookup_enemies
    #which sets miny/maxy values via monsterrandomizer.updatePos()
    
    #for m in monsters:
        #print(m.name + " | " + str(m.miny) + " | " + str(m.maxy))
    #input("X")
    fsets = get_fsets(sourcefile)
    locations = get_locations(outfile)


    #WC TESTING SPACE
    #improve_item_display(fout) #"works" but screws up battle text
    
    #this compiles but need to test if this is even needed in WC
    #allergic_dog(fout) 
    
    #cycle_statuses(fout) - doesnt work
    #name_swd_techs(fout) - dont bother    

    #testing commands
    #commands = commands_from_table(COMMAND_TABLE)
    #commands = {c.name:c for c in commands}
    #manage_commands(commands)

    ####the truly randomized BC commands don't work, crash game:
    #manage_commands(commands, command_no_guarantee_itemmagic="y", command_more_duplicates="y")
    
    #freespaces = manage_commands_new(commands)

    ######need this to show randomized "commands" section in log
    original_rom_location = sourcefile
    character.load_characters(original_rom_location, force_reload=True)
    characters = get_characters()

    commands = commands_from_table(COMMAND_TABLE)
    commands = {c.name:c for c in commands}

    #do this to get randomized Command Change features in the item section to work
    for c in characters:
        c.read_battle_commands(original_rom_location)
        #print(c.battle_commands)

    ######^ need this to show randomized "commands" section in log

    ######testing various thigns

    ##### begin of rom expansion validation. not actually called
    def validate_rom_expansion():
        # Some randomizer functions may expand the ROM past 32mbit. (ExHIROM)
        # Per abyssonym's testing, this needs bank 00 to be mirrored in bank 40.
        # While the modules that may use this extra space already handle this,
        # BC may make further changes to bank 00 afterward, so we need to mirror
        # the final version.
        fout.seek(0, 2)
        romsize = fout.tell()
        if romsize > 0x400000:
            # Standardize on 48mbit for ExHIROM, for now
            if romsize < 0x600000:
                expand_sub = Substitution()
                expand_sub.set_location(romsize)
                expand_sub.bytestring = bytes([0x00] * (0x600000 - romsize))
                expand_sub.write(fout)

            fout.seek(0)
            bank = fout.read(0x10000)
            fout.seek(0x400000)
            fout.write(bank)

    def rewrite_checksum(filename: str = None):
        # This assumes the file is 32, 40, 48, or 64 Mbit.
        if filename is None:
            filename = outfile
        MEGABIT = 0x20000
        f = open(filename, 'r+b')
        f.seek(0, 2)
        file_mbits = f.tell() // MEGABIT
        f.seek(0)
        subsums = [sum(f.read(MEGABIT)) for _ in range(file_mbits)]
        while len(subsums) % 32:
            subsums.extend(subsums[32:file_mbits])
            if len(subsums) > 64:
                subsums = subsums[:64]
        checksum = sum(subsums) & 0xFFFF
        f.seek(0xFFDE)
        write_multi(f, checksum, length=2)
        f.seek(0xFFDC)
        write_multi(f, checksum ^ 0xFFFF, length=2)
        if file_mbits > 32:
            f.seek(0x40FFDE)
            write_multi(f, checksum, length=2)
            f.seek(0x40FFDC)
            write_multi(f, checksum ^ 0xFFFF, length=2)

        f.close()
    ##### end of rewrite_checksum. not actually called

    #monsters = manage_monsters()
    #note that normal BC calls randomize_magicite from esperrandomizer prior to running this
    
    #mgs = manage_monster_appearance(monsters,preserve_graphics=False,monstersprites="y",monsterpalettes="n")
    #manage_colorize_animations()

    #items = get_ranked_items()
    #manage_items(items, changed_commands=changed_commands)
    #items = get_ranked_items() #this pulls in vanilla "ranking"

    
    #allows items/relics to be equipped as weapon/shields
    #manage_equip_anything()

####OPTIONAL TESTS
    print("\nRando options (use y/n for all options)\n")

    #skip rando section
    MonsterStatRando = "n"
    RandomMusicFlag = "n"
    RandomizeMonsterSprites = "n"
    SkipRando = input("Skip all rando (testing/debug)? (y/n)   ")
    if SkipRando == "n":
############################single patches
        YEquipRelicFlag = input("Apply Y Equip/Relic patch? (y/n)   ")
        if YEquipRelicFlag == "y":
            y_equip_relics(fout)  #y to switch in equip/relic menus
            print("Y Equip/Relic patch applied!")

        ColiseumRunFlag = input("Apply 'Run From Coliseum' patch? (y/n)   ")
        if ColiseumRunFlag == "y":
            #implement running in coliseum
            #https://github.com/seibaby/ff3us/blob/master/ff6_bank_c2_battle.asm
            #search for C25BE2.
            #25BEF is: BNE C25C1A     ;exit if in Colosseum
            #set this to EA * 2   <- NOP x 2?
            coliseum_run_sub = Substitution()
            coliseum_run_sub.bytestring = [0xEA] * 2
            coliseum_run_sub.set_location(0x25BEF)
            coliseum_run_sub.write(fout)
            print("Run From Coliseum patch applied!")

        EquipAnythingFlag = input("Apply 'Equip Anything' patch? Allows all items including items/relics to be \
equipped in weapon/shield slots, by all characters.  (y/n)   ")
        if EquipAnythingFlag == "y":
            manage_equip_anything()
            print("Equip Anything patch applied!")

        AllBerserkFlag = input("Make all characters uncontrollable/Coliseum AI? BC 'playsitself' flag.   (y/n)     ")
        if AllBerserkFlag == "y":
            full_umaro_sub = Substitution()
            full_umaro_sub.bytestring = bytes([0x80])
            full_umaro_sub.set_location(0x20928)
            full_umaro_sub.write(fout)
            #how necessary is this
            for c in commands.values():
                if c.id not in [0x01, 0x08, 0x0E, 0x0F, 0x15, 0x19]:
                    c.allow_while_berserk(fout)

        RandomizeAnimationsFlag = input("Randomize animation colors?   (y/n)    ")
        if RandomizeAnimationsFlag == "y":
            manage_colorize_animations()
            print("Animation colors randomized!")


        RandomizeMapPalettes = input("Randomize map colors?   (y/n)    ")
        if RandomizeMapPalettes == "y":
            manage_colorize_dungeons()
            print("Map colors randomized!")
        ###########grab playsitself from work laptop################

        RandomizeMonsterSprites = input("Randomize monster sprites using remonsterate (can pick sprites from other \
games)? Requires external ROM expansion.  (y/n)   ")

############################single patches
            
        #where the randomized exits are set    
        EntranceRandoFlag = input("Randomize entrances? (y/n)   ")
        if EntranceRandoFlag == "y":
            write_all_locations_misc()
            print("Entrances randomized!")

        #where the randomized monster abilities/stats are set    
        MonsterStatRando = input("Randomize monster abilities/stats/appearances? (y/n)   ")
        if MonsterStatRando == "y":
            MonsterRandoSpecify = input("Specify monster rando aspects? 'n' will apply all randomization options  (y/n)  ")
            if MonsterRandoSpecify == "n":
                monsterstats1 = "y"
                monsterstats2 = "y"
                monstermisc = "y"
                monsterautostatus = "y"
                monsterelemental = "y"
                monsterspecials = "y"
                monsters_darkworld = "y"
                monsterscripts = "y"
                monstercontrol = "y"
                monsterdrops = "y"
                monstersteals = "y"
                monstermorphs = "y"
                vanillacontrol = "n"
                monsterSketchRage = "y"
                vanillaSketchRage = "n"
                monstersprites = "y"
                monsterpalettes = "y"
                easybossupgrades = "y"
            if MonsterRandoSpecify == "y":
                print("WC scaling options will still apply to changed enemy stats.\n\n")
                
                monsterstats1 = input("Randomize base stats pt1: speed, attack, hitrate, evade, mblock, def, mdef, magpwr. \
Randomized based on level such that higher level monsters have higher potential to increase, while lower level monsters \
have less chance to be much different from their vanilla values   ")
                monsterstats2 = input("Randomize base stats pt2: HP, MP values. Randomized based on level such that higher \
level monsters have higher potential to increase, while lower level monsters have less chance to be much different from \
their vanilla values   ")
                monstermisc = input("Randomize escapability, scan-ability, undead flags.   ")
                monsterautostatus = input("Randomize auto-statuses and status immunities.   ")
                monsterelemental = input("Randomize elemental absorption, nullifcation, and weaknesses. Weaknesses can \
be scanned, if the enemy is scan-able.   ")
                monsterspecials = input("Randomize monster special abilities. This can affect Rages that use monster specials.   ")
                monsters_darkworld = input("Randomize monster special abilities even more (increases difficulty). \
BC option darkworld    ")
                monsterscripts = input("Randomize monster scripts (will override WC ability scaling element/random).   ")
                monstercontrol = input("Randomize monster Control commands.   ")
                if monstercontrol == "y":
                    vanillacontrol = input("Limit randomized Control commands to an individual monster's vanilla abilities.   ")
                else:
                    vanillacontrol = "n"
                monsterSketchRage = input("Randomize monster Sketch and Rage commands.   ")
                if monsterSketchRage == "y":
                    vanillaSketchRage = input("Limit randomized Sketch and Rage commands to an individual monster's vanilla abilities.   ")
                else:
                    vanillaSketchRage = "n"                    
                monsterdrops = input("Randomize monster drops.   ")
                monstersteals = input("Randomize monster steals.   ")
                monstermorphs = input("Randomize monster Ragnarok metamorphs.   ")                
                monstersprites = input("Randomize monster sprites.   ")
                monsterpalettes = input("Randomize monster palettes.   ")
                easybossupgrades = input("Make easier/early-game bosses more difficult.     ")

            #modify manage_monster inputs to take into account more options
            #1. modify base level, stats, HP/MP/XP/GP (each can be done individually)
            #2. modify escapability, scannable, undead
            #3. modify auto-statuses and status immunities
            #4. modify elemental absorb, null, weaknesses
            #5. modify specials (and/or their animations)
            #6. modify battle scripts
            #7. modify Control menu
            #8. modify drop table
            #9. modify steal table
            #10. modify Ragnarok metamorph table
            #an exclusion list can be passed along to prevent specific monsters from being edited
            #not sure about a specific list to guarantee changes
            monsters = manage_monsters(monsterstats1=monsterstats1, monsterstats2=monsterstats2, monstermisc=monstermisc,
                                       monsterautostatus=monsterautostatus, monsterelemental=monsterelemental, monsterspecials=monsterspecials,
                                       monsters_darkworld=monsters_darkworld, monsterscripts=monsterscripts, monstercontrol=monstercontrol,
                                       monsterdrops=monsterdrops, monstersteals=monstersteals, monstermorphs=monstermorphs,
                                       vanillacontrol=vanillacontrol, monsterSketchRage=monsterSketchRage, vanillaSketchRage=vanillaSketchRage,
                                       easybossupgrades=easybossupgrades)

            mgs = manage_monster_appearance(monsters,preserve_graphics=False, monstersprites=monstersprites,monsterpalettes=monsterpalettes)

            print("Monster stats/abilities randomized!")

        items = get_ranked_items() #this pulls in vanilla "ranking"
        #UltimateFlag = input("Replace weak items with FFVIA ultimate weapons?  (y/n)  ")
        #if UltimateFlag == "y":
            #ultimates(items, changed_commands=changed_commands)

        ItemRandoFlag = input("Randomize items? (y/n)  ")
        if ItemRandoFlag == "y":
            item_wild_breaks = "n"
            ItemRandoSpecify = input("Specify item rando aspects? 'n' will apply all randomization options  (y/n)  ")
            if ItemRandoSpecify == "n":
                itemstats1 = "y"
                itemstats2 = "y"
                itembreakproc = "y"
                itemteacher = "y"
                itemelemental = "y"
                itemspecial = "y"
                itemfeature = "y"
                itemheavy = "y"
                item_wild_breaks = "y"
                item_extra_effects = "y"
            if ItemRandoSpecify == "y":
                print("% chances are for each individual item\n\n")
                itemstats1 = input("Randomize item stats pt1: atk/def, hit/mdef values are \
    randomized such that original values closer 127 get varied the most (by up to 33%)   ")
                itemstats2 = input("Randomize item stats pt2: vig/spd/magpwr/sta, evade/mblock \
    are slightly randomized (+/- 1 or +/- 10 Evade/MBlock)   ")
                itembreakproc = input("Chance to add a proc/break effect   ")
                itemspecial = input("~2% chance to add a special action: \
    Can steal, Atma, X-kill, Man eater, Drain HP, Drain MP, Uses some MP, Random throw, \
    Dice, Valiant, Wind Attack, Heals Target, Slice Kill, Fragile wpn, Uses more MP   ")
                itemteacher = input("Chance to teach a spell   ")
                itemelemental = input("~6% chance to modify elemental properties: weapon element, \
    elemental halve, nullify, absorb, weakness   ")
                itemfeature = input("~4% chance to add a feature from one of the following \
    categories: \n 1) Atlas Armlet, Earrings x2, +1/2, 1/4, 1/8 HP, +1/2, 1/4, 1/8 MP \n 2) Earrings \
    Better Steal, Better Sketch, Better Control, 100% Hit Rate (Sniper Sight), 1/2 MP Cost, \
    MP cost = 1, Vigor +50% (Hyper Wrist) \n 3) Initiative (Gale Hairpin), Vigilance (Back Guard) \
    Fight->Jump, Magic->X Magic, Sketch->Control, Slot->GP Rain, Steal->Capture, Super Jump \
    (Dragon Horn) \n 4) Fight -> X-Fight (Offering), Counter (Black Belt), Random Evade (Beads), \
    2-hand weapons (Gauntlet), Equip 2 weapons (Genji Glove), Merit Award, Cover (True Knight), \
    Step regen (Tintinabar) \n 5) Status Protection: No dark, No zombie, No poison, No magitek \
    (prevents Magitek armor from overriding commands), No clear, No imp, No petrify, Death \
    protection (Safety Bit) \n 6) Status Protection: No condemned, Near fatal always, No image, \
    No mute, No berserk, No muddle, No seizure, No sleep \n 7) Auto-status: Condemned, Near \
    fatal, Image, Mute, Berserk, Muddle, Seizure, Sleep \n 8) Auto-status: Auto float, Auto \
    regen, Auto slow, Auto haste, Auto stop, Auto shell, Auto safe, Auto reflect \n 9) Field \
    effect: 1/2 enc (Charm Bangle), No enc (Moogle Charm)   ")
                itemheavy = input("5% chance to allow an item to be equipped using Merit Award \
    when it currently is not allowed (e.g. SnowMuffler)   ")
#                item_wild_breaks = input("Allow break/procs to access more random abilities \
#    (experimental). BC option wild_breaks    ")
                item_extra_effects = input("Add an additional 33% chance to add a special action, \
an additional 50% chance to add a feature, and an additional repeating 33% chance to add a \
    feature (every time a feature is added, give an additional 33% chance to add another one. \
    BC option extra_effects   ")

            #item randomization section
            #1 modify stats (atk/def, hit/mdef, vig/spd/magpwr/sta, evade/mblock
            #2 modify price (likely skip for WC)
            #3 modify break effects
            #4 modify proc effects
            #5 modify special actions: "Can steal", "Atma", "X-kill", "Man eater", "Drain HP", "Drain MP", "Uses some MP", "Random throw", "Dice", "Valiant", "Wind Attack", "Heals Target", "Slice Kill", "Fragile wpn", "Uses more MP", ]
            #6 modify spell learning
            #7 modify elemental properties
            #8 modify "features" - stat mods, command improve, relic-type effects, status protect, auto-status, field effect like Moogle Charm, procs
            #9 modify heaviness (Merit Award-ability)
            #items = get_ranked_items() #this pulls in vanilla "ranking"
            manage_items(items, changed_commands=changed_commands, 
                         itemstats1=itemstats1, itemstats2=itemstats2, itembreakproc=itembreakproc,
                         itemteacher=itemteacher, itemelemental=itemelemental, itemspecial=itemspecial,
                         itemfeature=itemfeature, itemheavy=itemheavy,
                         item_wild_breaks=item_wild_breaks, item_extra_effects=item_extra_effects)
            #to see the impact of manage_items on stats you need to check out the BC generated log and convert the speedvigor/magstam values into more meaningful things.
            #improve_item_display(fout) #this prob breaks

            from itemrandomizer import set_item_changed_commands
            set_item_changed_commands(changed_commands)

            #mutate_feature() is what gives items command changes

            #there are 5 "Command Change" feature slots available for items            
            #while items are given these features in mutate_features, which commands
            #are changed to new commands are actually set in reset_special_relics,
            #which also provides a format for the spoiler log
            if itemfeature == "y" or item_extra_effects == "y":
                loglist = reset_special_relics(items, characters, fout)
                #print(loglist)
            else:
                #the default loglist will just be the 5 Relics
                loglist = []
                loglist.append(("Coin Toss", 15, 24))
                loglist.append(("DragoonBoots", 0, 22))
                loglist.append(("FakeMustache", 13, 14))
                loglist.append(("Gem Box", 2, 23))
                loglist.append(("Thief Glove", 5, 6))
                #print(loglist)

            #provide the command change items to the spoiler log
            for name, before, after in loglist:
                beforename = [c for c in commands.values() if c.id == before][0].name
                aftername = [c for c in commands.values() if c.id == after][0].name
                logstr = "{0:13} {1:7} -> {2:7}".format(name + ":", beforename.lower(), aftername.lower())
                log(logstr, section="command-change relics")

            print("Items randomized!")


        CommandRandoFlag = input("Randomize commands? This may cause issues with learning SwdTech/Blitzes if the WC flags 'Everyone Learns' are off. (y/n)   ")
        if CommandRandoFlag == "y":
            CommandRandoSpecify = input("Specify command rando aspects? 'n' will apply all randomization options  (y/n)  ")
            if CommandRandoSpecify == "n":
                command_no_guarantee_itemmagic = "y"
                command_more_duplicates = "y"
            if CommandRandoSpecify == "y":
                command_no_guarantee_itemmagic = input("First, remove Magic and Item from every character's command. Next, give a 50% chance to have the \
Item command, and a separate 50% chance to have the Magic command.   ")
                command_more_duplicates = input("Increase the chance of duplicate commands? Overrules the 50% guarantee above. (experimental)   ")
            #command randomization section - note that this completely overwrites WC command randomization
            #1 gives a 50% chance of having a magic menu, and a separate 50% chance of an item menu. Replacements are pulled from other commands
            #2 optional switch (currently disabled) swap random unique commands for pure random, allows for more duplicate commands
            manage_commands(commands, command_no_guarantee_itemmagic=command_no_guarantee_itemmagic, command_more_duplicates=command_more_duplicates)

            #experimental
            #freespaces = manage_commands_new(commands)

        #where the randomized musics are set
        RandomMusicFlag = input("Randomize music (johnnydmad)? (y/n)   ")
        if RandomMusicFlag == "y":
            ChaosMusicFlag = input("Chaotic music? (y/n)   ")
            chaosmusic = False
            if ChaosMusicFlag == "y":
                chaosmusic = True
            randomize_music(fout, Options_, opera=None, form_music_overrides={},chaoticmusic=chaosmusic) #swap chaotic to false for "appropriate" music
            print("Music randomized!")

        # ----- NO MORE RANDOMNESS PAST THIS LINE -----
    else:
        y_equip_relics(fout)  #y to switch in equip/relic menus
        print("Y Equip/Relic patch applied!")
        coliseum_run_sub = Substitution()
        coliseum_run_sub.bytestring = [0xEA] * 2
        coliseum_run_sub.set_location(0x25BEF)
        coliseum_run_sub.write(fout)
        print("Run From Coliseum patch applied!")
        manage_colorize_animations()
        print("Animation colors randomized!")

        monsters = manage_monsters(monsterstats1="n",
                                   monsterstats2="n",
                                   monstermisc="n",
                                   monsterautostatus="n",
                                   monsterelemental="n",
                                   monsterspecials="y",
                                   monsters_darkworld="y",
                                   monsterscripts="y",
                                   monstercontrol="n",
                                   monsterdrops="y",
                                   monstersteals="n",
                                   monstermorphs="n",
                                   vanillacontrol="y",
                                   monsterSketchRage="n",
                                   vanillaSketchRage="y",
                                   easybossupgrades="y")

        mgs = manage_monster_appearance(monsters,preserve_graphics=False,
                                        monstersprites="n",
                                        monsterpalettes="y")

    #end of    if SkipRando == "n":

    ######need this to show randomized "commands" section in log
    for c in sorted(characters, key=lambda c: c.id):
        c.associate_command_objects(list(commands.values()))
        if c.id > 13:
            continue
        log(str(c), section="characters")

    ### check for remonsterate option here, after other code has run
    if RandomizeMonsterSprites == "y":
    #remonsterate code from BC
        fout.close()
        backup_path = outfile[:outfile.rindex('.')] + '.backup' + outfile[outfile.rindex('.'):]
        copyfile(src=outfile, dst=backup_path)
        attempt_number = 0
        remonsterate_results = None

        while True:
            try:
                kwargs = {
                    "outfile": outfile,
                    "seed": (seed + attempt_number),
                    "rom_type": "1.0",
                    "list_of_monsters": get_monsters(outfile)
                }
                pool = multiprocessing.Pool()
                x = pool.apply_async(func=remonsterate, kwds=kwargs)
                remonsterate_results = x.get()
                pool.close()
                pool.join()

            except OverflowError as e:
                print("Remonsterate: An error occurred attempting to remonsterate. Trying again...")
                # Replace backup file
                copyfile(src=backup_path, dst=outfile)
                attempt_number = attempt_number + 1
                continue
            break

        # Remonsterate finished
        fout = open(outfile, "r+b")
        os.remove(backup_path)
        if remonsterate_results:
            for result in remonsterate_results:
                log(str(result) + '\n', section='remonsterate')
            print("Monster sprites randomized via remonsterate!")
    #end of remonsterate code. untested with other monster sprite features

    #WC testing
    #formations = get_formations()
    #fsets = get_fsets()
    #WC testing
    
    #this needs to be written to work? usually called right after randomizing formations    
    for fs in fsets:
        fs.write_data(fout)

    #WC testing
    #for f in get_formations():
        #f.write_data(fout)
    
    #validate_rom_expansion()
    #rewrite_checksum()
    #WC testing
    
    fout.close()

    f = open(outlog, 'w+')

    if MonsterStatRando == "y":
        zones = get_zones(sourcefile)
        get_metamorphs(sourcefile)
        for m in sorted(get_monsters(), key=lambda m: m.display_name):
            if m.display_name:
                log(m.get_description(changed_commands=changed_commands),
                    section="monsters")
                
    if RandomMusicFlag == "y":
        log(get_music_spoiler(), section="music")

    f.write(get_logstring(["characters", "stats", "aesthetics", "commands", "blitz inputs", "slots", "dances", "espers", "item magic",
                           "item effects", "command-change relics", "colosseum", "monsters", "music", "remonsterate", "shops",
                           "treasure chests", "zozo clock"]))
        
    f.close()

    print("Randomization successful. Output filename: %s\n" % outfile)

    return outfile


if __name__ == "__main__":
    args = list(argv)
    if len(argv) > 3 and argv[3].strip().lower() == "test" or TEST_ON:
        randomize(args=args)
        sys.exit()
    try:
        randomize(args=args)
        input("Press enter to close this program. ")
    except Exception as e:
        print("ERROR: %s" % e)
        import traceback
        traceback.print_exc()
        if fout:
            fout.close()
        if outfile is not None:
            print("Please try again with a different seed.")
            input("Press enter to delete %s and quit. " % outfile)
            os.remove(outfile)
        else:
            input("Press enter to quit. ")
