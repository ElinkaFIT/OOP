# -----------------------------------------------------------
# Interpret IPPcode23: 2. úloha do IPP 2022/2023
# Jméno a přímení: Alena Kimecká
# xlogin: xklime47
# -----------------------------------------------------------

import argparse
import re
import xml.etree.ElementTree as ET
import sys

# -----------------------------------------------------------
# Slovník jednolivých instrukcí a jejich argumentů pro potřeby
# kontroly validity xml dokumentu
# -----------------------------------------------------------
ERROR_0 = 0  # bez chyby
ERROR_10 = 10  # chybějící parametr skriptu nebo zakázaná kombinace parametrů
ERROR_11 = 11  # chyba při otevírání vstupných souborů
ERROR_12 = 12  # chyba při otevření pro zápis
ERROR_31 = 31  # chybný formát XML
ERROR_32 = 32  # neočekávaná struktura XML
ERROR_52 = 52  # chyba sémenatické kontroly

# -----------------------------------------------------------
# Běhové chyby
# -----------------------------------------------------------
ERROR_53 = 53  # špatné typy operandů
ERROR_54 = 54  # přístup k neexistující proměnné
ERROR_55 = 55  # rámec neexistuje
ERROR_56 = 56  # chybějící hodnota
ERROR_57 = 57  # špatná hodnota operandu
ERROR_58 = 58  # chybná práce s řetězcem

# -----------------------------------------------------------
# Interní chyby
# -----------------------------------------------------------
ERROR_99 = 99  # interní chyba


# -----------------------------------------------------------
# Help zpráva obsahuje také help k rozšíření v kategorii extension
# -----------------------------------------------------------
HELP = """usage: python3 interpret.py [-h|--help] [-s|--source SOURCE] [-i|--input INPUT]

options:
    -h, --help          
                        show this help message and exit
    -s=SOURCE, --source=SOURCE
                        optional path for source file
    -i=INPUT, --input=INPUT
                        optional path for input file§
                        
extension:
    --stats=PATH 
                        must be given to activate path
    --insts
                        number of instructions
    --hot
                        most used instructions
    --vars
                        most variables in one time
    --frequent
                        most frequent instructions
    --print=STRING
                        can be used more than one time print given text
    --eol
                        print new line                    
    """

# -----------------------------------------------------------
# Slovník jednolivých instrukcí a jejich argumentů pro potřeby
# kontroly validity xml dokumentu
# -----------------------------------------------------------
OPCODE_REQUIREMENTS = {
    "MOVE": ["var", "symb"],
    "CREATEFRAME": [],
    "PUSHFRAME": [],
    "POPFRAME": [],
    "DEFVAR": ["var"],
    "CALL": ["label"],
    "RETURN": [],
    "PUSHS": ["symb"],
    "POPS": ["var"],
    "ADD": ["var", "symb", "symb"],
    "SUB": ["var", "symb", "symb"],
    "MUL": ["var", "symb", "symb"],
    "IDIV": ["var", "symb", "symb"],
    "LT": ["var", "symb", "symb"],
    "GT": ["var", "symb", "symb"],
    "EQ": ["var", "symb", "symb"],
    "AND": ["var", "symb", "symb"],
    "OR": ["var", "symb", "symb"],
    "NOT": ["var", "symb"],
    "INT2CHAR": ["var", "symb"],
    "STRI2INT": ["var", "symb", "symb"],
    "READ": ["var", "type"],
    "WRITE": ["symb"],
    "CONCAT": ["var", "symb", "symb"],
    "STRLEN": ["var", "symb"],
    "GETCHAR": ["var", "symb", "symb"],
    "SETCHAR": ["var", "symb1", "symb"],
    "TYPE": ["var", "symb"],
    "LABEL": ["label"],
    "JUMP": ["label"],
    "JUMPIFEQ": ["label", "symb", "symb"],
    "JUMPIFNEQ": ["label", "symb", "symb"],
    "EXIT": ["symb"],
    "DPRINT": ["symb"],
    "BREAK": [],
    # rozšíření
    "CLEARS": [],
    "ADDS": [],
    "SUBS": [],
    "MULS": [],
    "IDIVS": [],
    "LTS": [],
    "GTS": [],
    "EQS": [],
    "ANDS": [],
    "ORS": [],
    "NOTS": [],
    "INT2CHARS": [],
    "STRI2INTS": [],
    "JUMPIFEQS": ["label"],
    "JUMPIFNEQS": ["label"]
}

# -----------------------------------------------------------
# XmlValidator
#
# Obsahuje metody validující vstupní xml soubor
# -----------------------------------------------------------


class XmlValidator:
    def __init__(self, interpret):
        self.interpret = interpret
        self.labels = []

    # validuje hlavičku vstupního xml souboru
    def header_validator(self):
        if self.interpret.arguments_validator.source_data.tag != "program":
            exit(ERROR_32)
        for attribute in self.interpret.arguments_validator.source_data.attrib:
            if attribute not in ["language", "name", "description"]:
                exit(ERROR_32)
        if "language" not in self.interpret.arguments_validator.source_data.attrib:
            exit(ERROR_31)
        if self.interpret.arguments_validator.source_data.attrib["language"] != "IPPcode23":
            exit(ERROR_32)

    # validuje tělo vstupního xml souboru
    def xml_body_validator(self):
        already_used_numbers = []
        for instruction in self.interpret.arguments_validator.source_data:
            if instruction.tag != "instruction":
                exit(ERROR_32)
            if instruction.attrib.get("opcode") is None or instruction.attrib.get("order") is None:
                exit(ERROR_32)
            if instruction.attrib.get("opcode").upper() not in OPCODE_REQUIREMENTS:
                exit(ERROR_32)
            if not instruction.attrib.get("order").isnumeric():
                exit(ERROR_32)
            if int(instruction.attrib.get("order")) < 1 or instruction.attrib.get("order") in already_used_numbers:
                exit(ERROR_32)
            already_used_numbers.append(instruction.attrib.get("order"))
            self.instruction_childs_validator(instruction)
            self.interpret.stats_manager.instructions_opcodes.append(instruction.attrib.get('opcode').upper())

    # validuje děti ve vstupním xml souboru
    def instruction_childs_validator(self, instruction):
        if len(instruction) != len(OPCODE_REQUIREMENTS[instruction.attrib.get("opcode").upper()]):
            exit(ERROR_32)
        tags = []
        args = ["arg1", "arg2", "arg3"]
        label_accept = "label"
        type_accept = "type"
        var_accept = "var"
        symb_accept = ["var", "bool", "string", "int", "nil"]

        for i, argument in enumerate(instruction):
            if "type" not in argument.attrib:
                exit(ERROR_32)
            if argument.attrib["type"] not in ["string", "int", "bool", "label", "type", "nil", "var"]:
                exit(ERROR_32)
            if len(instruction) >= (i + 1) and args[i] == argument.tag:
                if OPCODE_REQUIREMENTS[instruction.attrib.get("opcode").upper()][i] == "label" and argument.attrib[
                    "type"] != label_accept:
                    exit(ERROR_32)
                elif OPCODE_REQUIREMENTS[instruction.attrib.get("opcode").upper()][i] == "type" and argument.attrib[
                    "type"] != type_accept:
                    exit(ERROR_32)
                elif OPCODE_REQUIREMENTS[instruction.attrib.get("opcode").upper()][i] == "var" and argument.attrib[
                    "type"] != var_accept:
                    exit(ERROR_32)
                elif OPCODE_REQUIREMENTS[instruction.attrib.get("opcode").upper()][i] == "symb" and argument.attrib[
                    "type"] not in symb_accept:
                    exit(ERROR_32)
            if instruction.attrib.get("opcode").upper() == "LABEL":
                if argument.text.strip() in self.labels:
                    exit(ERROR_52)
                self.labels.append(argument.text.strip())
            tags.append(argument.tag)

        for i in range(len(tags)):
            if args[i] not in tags:
                exit(ERROR_32)


# -----------------------------------------------------------
# ArgumentsValidator
#
# Validuje vstupní přepínače a kontroluje zda má uživatel
# pouštící program práva vytvářet a číst ze souborů
# -----------------------------------------------------------
class ArgumentsValidator:
    def __init__(self, interpret):
        self.interpret = interpret
        self.arguments = None
        self.args_parser = None
        self.source_data = None
        self.input_data = None
        self.input_file = None

    # Vytváří parser z knihovny argparse který parsuje vstupní parametry a následně
    # dochází k jejich validaci
    def get_arguments(self):
        try:
            arg_parser = argparse.ArgumentParser(add_help=False, exit_on_error=True)
            arg_parser.add_argument("-h", "--help", action='store_true')
            arg_parser.add_argument("-i", "--input", type=str)
            arg_parser.add_argument("-s", "--source", type=str)
            arg_parser.add_argument("--stats", type=str)
            arg_parser.add_argument("--insts", action='store_true')
            arg_parser.add_argument("--hot", action='store_true')
            arg_parser.add_argument("--vars", action='store_true')
            arg_parser.add_argument("--frequent", action='store_true')
            arg_parser.add_argument("--print", nargs='*', action='append', type=str)
            arg_parser.add_argument("--eol", action='store_true')
            args = arg_parser.parse_args()
        except:
            exit(ERROR_10)

        self.arguments = sys.argv[1:]
        if 1 < (len(list(filter(lambda arg: "--source" in arg, self.arguments))) +
                len(list(filter(lambda arg: arg[2] == '=' and "-s" in arg, self.arguments)))):
            exit(ERROR_10)
        if 1 < (len(list(filter(lambda arg: "--input" in arg, self.arguments))) +
                len(list(filter(lambda arg: arg[1] != '-' and "-i" in arg, self.arguments)))):
            exit(ERROR_10)
        if 1 < len(list(filter(lambda arg: "--stats" in arg, self.arguments))):
            exit(ERROR_10)

        if args.help:
            if args.input is not None or args.source is not None or args.stats is not None or args.insts or \
                    args.hot or args.vars or args.frequent or args.eol or args.print is not None:
                exit(ERROR_10)
            else:
                print(HELP)
                exit(ERROR_0)

        if args.stats is None and (args.insts or args.hot or args.vars or args.frequent or args.eol or
                                   args.print is not None):
            exit(ERROR_10)

        self.interpret.stats_manager.stats_file = vars(args).get('stats')
        self.args_parser = args

        if args.input is None and args.source is None:
            exit(ERROR_10)
        self.load_data(args)

    # Obsluhuje kontrolu xml vstupu a seřazuje objekty xml podle jejich
    # order pro snažší vykonávání programu a načítá vstup a kontroluje práva uživatele
    def load_data(self, args):
        try:
            if args.source is None:
                self.source_data = ET.fromstring(sys.stdin.read())

            else:
                source_file = ET.parse(args.source)
                self.source_data = source_file.getroot()
        except:
            exit(ERROR_31)

        self.interpret.xml_validator.header_validator()
        self.interpret.xml_validator.xml_body_validator()

        self.source_data[:] = sorted(self.source_data, key=lambda child: int(child.get('order')))

        for c in self.source_data:
            c[:] = sorted(c, key=lambda child: child.tag)

        if args.input is None:
            self.input_data = sys.stdin.read().splitlines()
        else:
            try:
                self.input_file = open(args.input, "r")
                self.input_data = self.input_file.read().splitlines()
            except:
                exit(ERROR_11)


# -----------------------------------------------------------
# StatsManager
#
# Validuje vstupní přepínače a kontroluje zda má uživatel
# pouštící program práva vytvářet a číst ze souborů
# -----------------------------------------------------------
class StatsManager:
    def __init__(self, interpret):
        self.interpret = interpret
        self.instructions_opcodes = []
        self.instructions_orders = []
        self.stats_file = None

    # Spočítá statistiky
    def calculate_stats(self):
        max_opcode = []
        max_opcode_frequency = 0
        for opcode in OPCODE_REQUIREMENTS:
            count = self.instructions_opcodes.count(opcode)
            if count == max_opcode_frequency:
                max_opcode.append(opcode)
            elif count > max_opcode_frequency:
                max_opcode = [opcode]
                max_opcode_frequency = count
        most_frequent_instruction = 0

        if len(self.instructions_orders) > 0:
            most_frequent_instruction = max(sorted(self.instructions_orders, key=lambda word: int(word)),
                                            key=self.instructions_orders.count)
        if self.stats_file is not None:
            self.print_stats(most_frequent_instruction, max_opcode)

    # Vypíše požadované statistiky do zadaného souboru
    def print_stats(self, most_frequent_instruction, max_opcode):
        print_index = 0
        try:
            stats_file = open(self.stats_file, "w")
        except:
            exit(ERROR_12)

        for argument in self.interpret.arguments_validator.arguments:
            splitted = len(argument.split("="))
            if "--print" in argument and splitted > 1:
                stats_file.write(vars(self.interpret.arguments_validator.args_parser).get('print')[print_index][0])
                print_index += 1
            if "--eol" in argument and splitted == 1:
                stats_file.write("\n")
            if "--hot" in argument:
                stats_file.write(str(most_frequent_instruction))
            if "--frequent" in argument and splitted == 1:
                for i, j in enumerate(max_opcode):
                    if i == 0:
                        stats_file.write(j)
                    else:
                        stats_file.write("," + j)
            if "insts" in argument and splitted == 1:
                stats_file.write(str(len(self.instructions_orders)))
            if "vars" in argument and splitted == 1:
                stats_file.write(str(self.interpret.frame_manager.max_var_count))


# -----------------------------------------------------------
# Utilities
#
# Poskytuje pomocné metody k práci
# -----------------------------------------------------------
class Utilities:
    def __init__(self, interpret):
        self.interpret = interpret

    # Konvertuje řetězce na bool
    def string_to_bool(self, value):
        if value.upper() == "TRUE":
            return True
        if value.upper() == "FALSE":
            return False

    # Přijme konstantu nebo proměnou a vrátí její hodnotu a typ
    def get_symb_data(self, symb):
        if symb[0] == 'var':
            split_symb = symb[1].split('@')
            if split_symb[0] == "GF":
                if self.interpret.frame_manager.gf.find_variable(split_symb[1]) is None:
                    exit(ERROR_54)
                new_symb = self.interpret.frame_manager.gf.find_variable(split_symb[1]).value
                v_type = self.interpret.frame_manager.gf.find_variable(split_symb[1]).v_type
            elif split_symb[0] == "TF":
                if self.interpret.frame_manager.tf is None:
                    exit(ERROR_55)
                elif self.interpret.frame_manager.tf.find_variable(split_symb[1]) is None:
                    exit(ERROR_54)
                new_symb = self.interpret.frame_manager.tf.find_variable(split_symb[1]).value
                v_type = self.interpret.frame_manager.tf.find_variable(split_symb[1]).v_type
            elif split_symb[0] == "LF":
                if self.interpret.frame_manager.lf_list.top is None:
                    exit(ERROR_55)
                elif self.interpret.frame_manager.lf_list.top.find_variable(split_symb[1]) is None:
                    exit(ERROR_54)
                new_symb = self.interpret.frame_manager.lf_list.top.find_variable(split_symb[1]).value
                v_type = self.interpret.frame_manager.lf_list.top.find_variable(split_symb[1]).v_type
            else:
                exit(ERROR_54)
        else:
            v_type = symb[0]
            if symb[1] is None:
                new_symb = ""
            else:
                new_symb = symb[1]
        return new_symb, v_type

    # Změní hodnotu proměnné na novou hodnotu
    def update_var(self, var, new_symb, new_type):
        if var[0] == "GF":
            if self.interpret.frame_manager.gf.find_variable(var[1]) is None:
                exit(ERROR_54)
            self.interpret.frame_manager.gf.find_variable(var[1]).update(new_symb, new_type)
        elif var[0] == "TF":
            if self.interpret.frame_manager.tf is None:
                exit(ERROR_55)
            elif self.interpret.frame_manager.tf.find_variable(var[1]) is None:
                exit(ERROR_54)
            self.interpret.frame_manager.tf.find_variable(var[1]).update(new_symb, new_type)
        elif var[0] == "LF":
            if self.interpret.frame_manager.lf_list.top is None:
                exit(ERROR_55)
            elif self.interpret.frame_manager.lf_list.top.find_variable(var[1]) is None:
                exit(ERROR_54)
            self.interpret.frame_manager.lf_list.top.find_variable(var[1]).update(new_symb, new_type)

    # Konvertuje řetězec s escape sekvencemi na prostý řetězec
    def convert_escaped_string(self, orig_string):
        new_string = orig_string
        replace_arr_len = len(re.findall(r"\\[0-9]{3}", new_string))
        replace_arr = re.findall(r"\\[0-9]{3}", new_string)

        if replace_arr_len > 0:
            for i in range(0, replace_arr_len):
                new_string = re.sub(r"\\[0-9]{3}", chr(int(replace_arr[i][2:])), new_string, count=1)

        return new_string


# -----------------------------------------------------------
# Interpret
#
# Obsahuje jádro programu vykonávající veškerou
# funkcionalitu a provedení daných XML instrukcí
# -----------------------------------------------------------
class Interpret:
    def __init__(self):
        self.frame_manager = FrameManager()
        self.xml_validator = XmlValidator(self)
        self.arguments_validator = ArgumentsValidator(self)
        self.stats_manager = StatsManager(self)
        self.utilities = Utilities(self)
        self.input_order = 0
        self.instr_order = 0

    # Projde všechny XML instrukce podle pořadí order, případně skáče podle zadaných instrukcí
    def iterator(self):
        while self.instr_order < len(self.arguments_validator.source_data):

            args = []
            for child_args in self.arguments_validator.source_data[self.instr_order]:
                if child_args.text is None:
                    args.append((child_args.attrib.get('type'), child_args.text))
                else:
                    args.append((child_args.attrib.get('type'), child_args.text.strip()))
            if self.arguments_validator.source_data[self.instr_order].attrib.get('opcode').upper() != "LABEL":
                self.stats_manager.instructions_orders.append(self.arguments_validator.source_data[self.instr_order].attrib.get('order'))
            self.switch(self.arguments_validator.source_data[self.instr_order].attrib.get('opcode'), args, self.instr_order,
                        self.arguments_validator.source_data[self.instr_order].attrib.get('order'))
            self.instr_order += 1
        self.stats_manager.calculate_stats()

    # -----------------------------------------------------------
    # switch
    #
    # Na základě zavolané instrukce dojde k provedení konkrétní instrukce
    # -----------------------------------------------------------
    def switch(self, instruction, args, instr_order, xml_order):
        match instruction.upper():
            case "MOVE":
                var = args[0][1].split('@')
                symb = args[1]
                self.f_move(var, symb)
            case "CREATEFRAME":
                self.f_createframe()
            case "PUSHFRAME":
                self.f_pushframe()
            case "POPFRAME":
                self.f_popframe()
            case "DEFVAR":
                var = args[0][1].split('@')
                self.f_defvar(var)
                self.frame_manager.max_vars()
            case "CALL":
                label = args[0]
                self.f_call(label, xml_order)
            case "RETURN":
                self.f_return()
            case "PUSHS":
                symb = args[0]
                self.f_pushs(symb)
            case "POPS":
                var = args[0][1].split('@')
                self.f_pops(var)
            case "ADD":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_numeric(var, symb, symb2, "add")
            case "SUB":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_numeric(var, symb, symb2, "sub")
            case "MUL":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_numeric(var, symb, symb2, "mul")
            case "IDIV":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_numeric(var, symb, symb2, "idiv")
            case "LT":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_lt_gt_eq(var, symb, symb2, "LT")
            case "GT":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_lt_gt_eq(var, symb, symb2, "GT")
            case "EQ":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_lt_gt_eq(var, symb, symb2, "EQ")
            case "AND":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_and_or_not(var, symb, symb2, "AND")
            case "OR":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_and_or_not(var, symb, symb2, "OR")
            case "NOT":
                var = args[0][1].split('@')
                symb = args[1]
                self.f_not(var, symb)
            case "INT2CHAR":
                var = args[0][1].split('@')
                symb = args[1]
                self.f_int2char(var, symb)
            case "STRI2INT":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_stri2int_getchar(var, symb, symb2, "STRI2INT")
            case "READ":
                var = args[0][1].split('@')
                v_type = args[1]
                self.f_read(var, v_type)
                self.input_order += 1
            case "WRITE":
                symb = args[0]
                self.f_write(symb)
            case "CONCAT":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_concat(var, symb, symb2)
            case "STRLEN":
                var = args[0][1].split('@')
                symb = args[1]
                self.f_strlen(var, symb)
            case "GETCHAR":
                var = args[0][1].split('@')
                symb = args[1]
                symb2 = args[2]
                self.f_stri2int_getchar(var, symb, symb2, "GETCHAR")
            case "SETCHAR":
                var = args[0]
                symb = args[1]
                symb2 = args[2]
                self.f_setchar(var, symb, symb2)
            case "TYPE":
                var = args[0][1].split('@')
                symb = args[1]
                self.f_type(var, symb)
            case "JUMP":
                label = args[0]
                self.f_jump(label, "LABEL", None)
            case "JUMPIFEQ":
                label = args[0]
                symb = args[1]
                symb2 = args[2]
                self.f_jumpifeq(label, symb, symb2)
            case "JUMPIFNEQ":
                label = args[0]
                symb = args[1]
                symb2 = args[2]
                self.f_jumpifneq(label, symb, symb2)
            case "EXIT":
                symb = args[0]
                self.f_exit(symb)
            case "DPRINT":
                symb = args[0]
                self.f_dprint(symb)
            case "BREAK":
                self.f_break(instr_order)
            case "CLEARS":
                self.frame_manager.stack.clear_stack()
            case "ADDS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_numeric(var, symbs[0], symbs[1], "add")
            case "SUBS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_numeric(var, symbs[0], symbs[1], "sub")
            case "MULS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_numeric(var, symbs[0], symbs[1], "mul")
            case "IDIVS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_numeric(var, symbs[0], symbs[1], "idiv")
            case "LTS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_lt_gt_eq(var, symbs[0], symbs[1], "LT")
            case "GTS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_lt_gt_eq(var, symbs[0], symbs[1], "GT")
            case "EQS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_lt_gt_eq(var, symbs[0], symbs[1], "EQ")
            case "ANDS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_and_or_not(var, symbs[0], symbs[1], "AND")
            case "ORS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_and_or_not(var, symbs[0], symbs[1], "OR")
            case "NOTS":
                var = ["stack", "stack"]
                symb = self.frame_manager.stack.get_top()
                self.f_not(var, symb)
            case "INT2CHARS":
                var = ["stack", "stack"]
                symb = self.frame_manager.stack.get_top()
                self.f_int2char(var, symb)
            case "STRI2INTS":
                var = ["stack", "stack"]
                symbs = self.frame_manager.stack.get_tops()
                self.f_stri2int_getchar(var, symbs[0], symbs[1], "STRI2INT")
            case "JUMPIFEQS":
                label = args[0]
                symbs = self.frame_manager.stack.get_tops()
                self.f_jumpifeq(label, symbs[0], symbs[1])
            case "JUMPIFNEQS":
                label = args[0]
                symbs = self.frame_manager.stack.get_tops()
                self.f_jumpifneq(label, symbs[0], symbs[1])

    # -----------------------------------------------------------
    # Práce s rámci
    # -----------------------------------------------------------
    # Přidá data do již inicializované proměnné
    def f_move(self, var, symb):
        new_symb = self.utilities.get_symb_data(symb)
        new_value = new_symb[0]
        if new_value is None:
            exit(ERROR_56)

        if new_symb[1] == "string":
            new_value = self.utilities.convert_escaped_string(new_value)

        self.utilities.update_var(var, new_value, new_symb[1])

    # Vytvoří dočasný rámec
    def f_createframe(self):
        self.frame_manager.create_tf()

    # Přesune dočasný rámec do zásobníku lokálních rámců
    def f_pushframe(self):
        self.frame_manager.push_lf()

    # Vymaže lokální rámec
    def f_popframe(self):
        self.frame_manager.pop_lf()

    # Stará se o deklaraci proměnné na odpovídajícím rámci
    def f_defvar(self, var):
        if var[0] == "GF":
            self.frame_manager.gf.add_variable(var[1])
        elif var[0] == "TF":
            if self.frame_manager.tf is None:
                exit(ERROR_55)
            else:
                self.frame_manager.tf.add_variable(var[1])
        elif var[0] == "LF":
            if self.frame_manager.lf_list.top is None:
                exit(ERROR_55)
            self.frame_manager.lf_list.top.add_variable(var[1])

    # -----------------------------------------------------------
    # Práce se skoky
    # -----------------------------------------------------------
    # Metoda zajistí skok na zadané návěští a uloží si adresu pro následný return
    def f_call(self, label, xml_order):
        self.frame_manager.call_stack.push_stack((label, xml_order))
        self.f_jump(label, "LABEL", None)

    # Metoda zajistí skok zpět na adresu ze které byl naposledy vykonán skok
    def f_return(self):
        if self.frame_manager.call_stack.top is None:
            exit(ERROR_56)
        jump_info = self.frame_manager.call_stack.pop_stack()
        self.f_jump(jump_info[0], "CALL", jump_info[1])

    # -----------------------------------------------------------
    # Práce s datovým zásobníkem
    # -----------------------------------------------------------
    # Přidá proměnnou do zásobníku
    def f_pushs(self, symb):
        new_symb = self.utilities.get_symb_data(symb)
        if new_symb[0] is None:
            exit(ERROR_56)
        self.frame_manager.stack.push_stack([new_symb[1], new_symb[0]])

    # Vymaže proměnnou ze zásobníku
    def f_pops(self, var):
        if self.frame_manager.stack.top is None:
            exit(ERROR_56)
        new_data = self.frame_manager.stack.pop_stack()
        self.utilities.update_var(var, new_data[1], new_data[0])

    # -----------------------------------------------------------
    # Aritmetické, relační, booleovské a konverzní instrukce
    # -----------------------------------------------------------
    # Provede instrukci add/sub/mul/div, podle zadané hodnoty oper
    def f_numeric(self, var, symb, symb2, oper):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)

        if new_symb1[0] is None or new_symb2[0] is None:
            exit(ERROR_56)
        if new_symb1[1] != "int" or new_symb2[1] != "int":
            exit(ERROR_53)

        if new_symb1[0][0] in ["+", "-"]:
            if not (new_symb1[0][1:].isdigit()):
                exit(ERROR_32)
        elif not (new_symb1[0].isdigit()):
            exit(ERROR_32)

        if new_symb2[0][0] in ["+", "-"]:
            if not (new_symb2[0][1:].isdigit()):
                exit(ERROR_32)
        elif not (new_symb2[0].isdigit()):
            exit(ERROR_32)

        if oper == "add":
            new_data = int(new_symb1[0]) + int(new_symb2[0])
        elif oper == "sub":
            new_data = int(new_symb1[0]) - int(new_symb2[0])
        elif oper == "mul":
            new_data = int(new_symb1[0]) * int(new_symb2[0])
        elif oper == "idiv":
            if int(new_symb2[0]) == 0:
                exit(ERROR_57)
            else:
                new_data = int(new_symb1[0]) // int(new_symb2[0])
        else:
            exit(ERROR_99)

        if var[0] == "stack":
            self.frame_manager.stack.push_stack(["int", str(new_data)])
        else:
            self.utilities.update_var(var, str(new_data), "int")

    # Provede instrukci </>/=, podle zadané hodnoty instruction
    def f_lt_gt_eq(self, var, symb, symb2, instruction):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)
        value_a = new_symb1[0]
        value_b = new_symb2[0]

        if value_a is None or value_b is None:
            exit(ERROR_56)

        if new_symb1[1] == "nil" or new_symb2[1] == "nil":
            if instruction in ["LT", "GT"]:
                exit(ERROR_53)
        elif new_symb1[1] != new_symb2[1]:
            exit(ERROR_53)
        else:
            if new_symb1[1] == "bool":
                value_a = self.utilities.string_to_bool(value_a)
                value_b = self.utilities.string_to_bool(value_b)
            elif new_symb1[1] == "int":
                value_a = int(value_a)
                value_b = int(value_b)
            elif new_symb1[1] == "string":
                value_a = self.utilities.convert_escaped_string(value_a)
                value_b = self.utilities.convert_escaped_string(value_b)

        if instruction == "LT":
            new_data = value_a < value_b
        elif instruction == "GT":
            new_data = value_a > value_b
        else:
            new_data = value_a == value_b

        if var[0] == "stack":
            self.frame_manager.stack.push_stack(["bool", str(new_data).lower()])
        else:
            self.utilities.update_var(var, str(new_data).lower(), "bool")

    # Provede instrukci and/or, podle zadané hodnoty instruction
    def f_and_or_not(self, var, symb, symb2, instruction):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)

        if new_symb1[0] is None or new_symb2[0] is None:
            exit(ERROR_56)
        if new_symb1[1] != "bool" or new_symb2[1] != "bool":
            exit(ERROR_53)
        if instruction == "AND":
            new_data = self.utilities.string_to_bool(new_symb1[0]) and self.utilities.string_to_bool(new_symb2[0])
        else:
            new_data = self.utilities.string_to_bool(new_symb1[0]) or self.utilities.string_to_bool(new_symb2[0])

        if var[0] == "stack":
            self.frame_manager.stack.push_stack(["bool", str(new_data).lower()])
        else:
            self.utilities.update_var(var, str(new_data).lower(), "bool")

    # Provede negaci
    def f_not(self, var, symb):
        new_symb1 = self.utilities.get_symb_data(symb)

        if new_symb1[0] is None:
            exit(ERROR_56)
        if new_symb1[1] != "bool":
            exit(ERROR_53)
        new_data = not self.utilities.string_to_bool(new_symb1[0])

        if var[0] == "stack":
            self.frame_manager.stack.push_stack(["bool", str(new_data).lower()])
        else:
            self.utilities.update_var(var, str(new_data).lower(), "bool")

    # Převede číslo na písmeno odpovídající jeho ASCII hodnotě
    def f_int2char(self, var, symb):
        new_symb = self.utilities.get_symb_data(symb)

        if new_symb[0] is None:
            exit(ERROR_56)
        if new_symb[1] != "int":
            exit(ERROR_53)
        try:
            new_data = chr(int(new_symb[0]))
        except:
            exit(ERROR_58)

        if var[0] == "stack":
            self.frame_manager.stack.push_stack(["string", str(new_data)])
        else:
            self.utilities.update_var(var, str(new_data), "string")

    # Provede instrukci stri2int nebo getchar dle zadané hodnoty instruction
    def f_stri2int_getchar(self, var, symb, symb2, instruction):
        string_base = self.utilities.get_symb_data(symb)
        position = self.utilities.get_symb_data(symb2)
        if position[0] is None or string_base[0] is None:
            exit(ERROR_56)
        if position[0][0] == "-":
            exit(ERROR_58)
        if position[1] != "int" or string_base[1] != "string" or not (position[0].isnumeric()):
            exit(ERROR_53)
        if len(string_base[0]) <= int(position[0]):
            exit(ERROR_58)

        new_base = self.utilities.convert_escaped_string(string_base[0])

        for i in range(0, len(new_base)):
            if i == int(position[0]):
                if instruction == "GETCHAR":
                    self.utilities.update_var(var, str(new_base[i]), "string")
                elif instruction == "STRI2INT":
                    new_data = ord(new_base[i])
                    if var[0] == "stack":
                        self.frame_manager.stack.push_stack(["int", str(new_data)])
                    else:
                        self.utilities.update_var(var, str(new_data), "int")
                break

    # -----------------------------------------------------------
    # Vstupně-výstupní instrukce
    # -----------------------------------------------------------
    # Metoda načítá data ze vstupu
    def f_read(self, var, v_type):
        new_data = self.arguments_validator.input_data
        try:
            test = new_data[self.input_order]
        except:
            self.utilities.update_var(var, "nil", "nil")
            return
        if new_data[self.input_order] is None:
            self.utilities.update_var(var, "nil", "nil")
        elif v_type[1] == "int":
            if new_data[self.input_order][0] in ["+", "-"]:
                if not (new_data[self.input_order][1:].isdigit()):
                    self.utilities.update_var(var, "nil", "nil")
                else:
                    self.utilities.update_var(var, new_data[self.input_order], "int")
            elif not (new_data[self.input_order].isdigit()):
                self.utilities.update_var(var, "nil", "nil")
            else:
                self.utilities.update_var(var, new_data[self.input_order], "int")
        elif v_type[1] == "bool":
            if new_data[self.input_order].upper() == "TRUE":
                self.utilities.update_var(var, "true", "bool")
            else:
                self.utilities.update_var(var, "false", "bool")
        elif v_type[1] == "string":
            converted_data = self.utilities.convert_escaped_string(new_data[self.input_order])
            self.utilities.update_var(var, converted_data, "string")
        else:
            self.utilities.update_var(var, "nil", "nil")

    # Metoda vypíše na standartní výstup obsah zadané proměnné
    def f_write(self, symb):
        new_symb = self.utilities.get_symb_data(symb)
        if new_symb[0] is None:
            exit(ERROR_56)
        if new_symb[1] == "string":
            print(self.utilities.convert_escaped_string(new_symb[0]), end="")
        elif new_symb[0] == "nil" and new_symb[1] == "nil":
            print("", end="")
        else:
            print(new_symb[0], end="")

    # -----------------------------------------------------------
    # Práce s řetězci
    # -----------------------------------------------------------
    # Spojí dva řetězce dohromady
    def f_concat(self, var, symb, symb2):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)
        if new_symb1[0] is None or new_symb2[0] is None:
            exit(ERROR_56)
        if new_symb1[1] != "string" or new_symb2[1] != "string":
            exit(ERROR_53)
        converted_string1 = self.utilities.convert_escaped_string(new_symb1[0])
        converted_string2 = self.utilities.convert_escaped_string(new_symb2[0])
        new_data = converted_string1 + converted_string2
        self.utilities.update_var(var, str(new_data), "string")

    # Vrátí délku vstupního řetězce
    def f_strlen(self, var, symb):
        new_symb = self.utilities.get_symb_data(symb)
        if new_symb[0] is None:
            exit(ERROR_56)
        if new_symb[1] != "string":
            exit(ERROR_53)
        converted_string = self.utilities.convert_escaped_string(new_symb[0])
        new_data = len(converted_string)
        self.utilities.update_var(var, str(new_data), "int")

    # Změní hodnotu proměnné nahrazením konkrétního znaku jiným
    def f_setchar(self, var, symb, symb2):
        variable = var[1].split('@')
        old_data = self.utilities.get_symb_data(var)
        position = self.utilities.get_symb_data(symb)
        new_symbol = self.utilities.get_symb_data(symb2)
        if position[0] is None or new_symbol[0] is None or old_data[0] is None:
            exit(ERROR_56)
        if old_data[0] == "" or new_symbol[0] == "":
            exit(ERROR_58)
        if position[1] != "int" or new_symbol[1] != "string" or old_data[1] != "string":
            exit(ERROR_53)

        if position[0][0] == "-":
            exit(ERROR_58)
        if len(old_data[0]) <= int(position[0]):
            exit(ERROR_58)

        position = int(position[0])
        new_character = self.utilities.convert_escaped_string(new_symbol[0])[0]
        for i in range(0, len(old_data[0])):
            if i == position:
                new_data = old_data[0][:position] + new_character + old_data[0][position + 1:]
                self.utilities.update_var(variable, str(new_data), "string")
                break

    # -----------------------------------------------------------
    # Práce s typy
    # -----------------------------------------------------------
    # Uloží typ proměnné
    def f_type(self, var, symb):
        new_symb = self.utilities.get_symb_data(symb)
        if new_symb[0] is None:
            new_data = ""
        else:
            new_data = new_symb[1]
        self.utilities.update_var(var, str(new_data), "string")

    # -----------------------------------------------------------
    # Práce se skoky
    # -----------------------------------------------------------
    # Provede skok na zadané návěští
    def f_jump(self, label, action, condition):
        for i, instruction in enumerate(self.arguments_validator.source_data):
            if instruction.attrib.get("opcode").upper() == action and instruction.find('arg1').text.strip() == label[1] \
                    and (condition is None or condition == instruction.attrib.get("order")):
                self.instr_order = i
                return
        exit(ERROR_52)

    # Provede podmíněný skok na zadané návěští pouze splňuje-li podmínku
    def f_jumpifeq(self, label, symb, symb2):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)
        converted_symb1 = new_symb1[0]
        converted_symb2 = new_symb2[0]
        if new_symb1[0] is None or new_symb2[0] is None:
            exit(ERROR_56)
        if new_symb1[1] == "string":
            converted_symb1 = self.utilities.convert_escaped_string(new_symb1[0])
        if new_symb2[1] == "string":
            converted_symb2 = self.utilities.convert_escaped_string(new_symb2[0])
        if new_symb1[1] == "nil" or new_symb2[1] == "nil":
            if converted_symb1 == converted_symb2:
                self.f_jump(label, "LABEL", None)
        elif new_symb1[1] != new_symb2[1]:
            exit(ERROR_53)
        elif label[1] not in self.xml_validator.labels:
            exit(ERROR_52)
        elif converted_symb1 == converted_symb2:
            self.f_jump(label, "LABEL", None)

    # Provede podmíněný skok na zadané návěští pouze nesplňuje-li podmínku
    def f_jumpifneq(self, label, symb, symb2):
        new_symb1 = self.utilities.get_symb_data(symb)
        new_symb2 = self.utilities.get_symb_data(symb2)
        converted_symb1 = new_symb1[0]
        converted_symb2 = new_symb2[0]

        if new_symb1[0] is None or new_symb2[0] is None:
            exit(ERROR_56)
        if new_symb1[1] == "string":
            converted_symb1 = self.utilities.convert_escaped_string(new_symb1[0])
        if new_symb2[1] == "string":
            converted_symb2 = self.utilities.convert_escaped_string(new_symb2[0])
        if new_symb1[1] == "nil" or new_symb2[1] == "nil":
            if converted_symb1 != converted_symb2:
                self.f_jump(label, "LABEL", None)
        elif new_symb1[1] != new_symb2[1]:
            exit(ERROR_53)
        elif label[1] not in self.xml_validator.labels:
            exit(ERROR_52)
        elif converted_symb1 != converted_symb2:
            self.f_jump(label, "LABEL", None)

    # -----------------------------------------------------------
    # Předčasné ukončení programu
    # -----------------------------------------------------------
    # Ukončí program se zadanou návratovou hodnotou v rozmezí 0-49
    def f_exit(self, symb):
        new_symb = self.utilities.get_symb_data(symb)
        if new_symb[0] is None:
            exit(ERROR_56)
        if new_symb[1] != "int":
            exit(ERROR_53)
        if new_symb[0][0] in ["+", "-"]:
            if not (new_symb[0][1:].isdigit()):
                exit(ERROR_57)
        elif not (new_symb[0].isdigit()):
            exit(ERROR_57)
        if int(new_symb[0]) > 49 or int(new_symb[0]) < 0:
            exit(ERROR_57)
        exit(int(new_symb[0]))

    # -----------------------------------------------------------
    # Ladící instrukce
    # -----------------------------------------------------------
    # Vypíše zadaná data na stderr
    def f_dprint(self, symb):
        new_symb1 = self.utilities.get_symb_data(symb)
        data_out = new_symb1[0]
        if new_symb1[1] == "string":
            data_out = self.utilities.convert_escaped_string(new_symb1[0])
        sys.stderr.write(data_out)

    # Vypíše ladící informace
    def f_break(self, instr_order):
        sys.stderr.write("Pozice instrukce: " + str(instr_order) + '\n')
        sys.stderr.write("Obsah GF: " + '\n')
        for var in self.frame_manager.gf.variable_list:
            sys.stderr.write(var.name + "|" + var.v_type + "|" + var.value + '\n')
        sys.stderr.write("Obsah LF: " + '\n')
        if not (self.frame_manager.lf_list.top is None):
            for var in self.frame_manager.lf_list.top.variable_list:
                sys.stderr.write(var.name + "|" + var.v_type + "|" + var.value + '\n')
        sys.stderr.write("Obsah TF: " + '\n')
        if not (self.frame_manager.tf is None):
            for var in self.frame_manager.tf.variable_list:
                sys.stderr.write(var.name + "|" + var.v_type + "|" + var.value + '\n')


# -----------------------------------------------------------
# FrameManager
#
# Zajištuje obsluhu a práci s rámcí
# -----------------------------------------------------------
class FrameManager:
    def __init__(self):
        self.gf = Frame()
        self.lf_list = Stack()
        self.tf = None
        self.stack = Stack()
        self.call_stack = Stack()
        self.max_var_count = 0

    # Vymaže lokální rámec ze zásobníku
    def pop_lf(self):
        if self.lf_list.top is None:
            exit(ERROR_55)
        else:
            self.tf = self.lf_list.top
            self.lf_list.pop_stack()

    # Přesune dočasný rámec do zásobníku lokálních rámců
    def push_lf(self):
        if self.tf is None:
            exit(ERROR_55)
        self.lf_list.push_stack(self.tf)
        self.tf = None

    # Vytvoří nový lokální rámec
    def create_tf(self):
        self.tf = Frame()

    # Určí zda je momenálně více proměných než je maximum
    def max_vars(self):
        count = self.count_variables()
        if count > self.max_var_count:
            self.max_var_count = count

    # Spočítá počet proměných ve všech rámcích
    def count_variables(self):
        count = self.gf.var_count
        if self.tf is not None:
            count += self.tf.var_count
        for frame in self.lf_list.data:
            count += frame.var_count
        return count


# -----------------------------------------------------------
# Frame
#
# Rámec a jeho funkcionalita
# -----------------------------------------------------------
class Frame:
    def __init__(self):
        self.variable_list = []
        self.var_count = 0

    # Přidá proměnnou do rámce
    def add_variable(self, name):
        for var in self.variable_list:
            if var.name == name:
                exit(ERROR_52)
        self.variable_list.append(Variable(name))
        self.var_count += 1

    # Najde proměnnou v rámci
    def find_variable(self, key):
        for var in self.variable_list:
            if var.name == key:
                return var
        exit(ERROR_54)


# -----------------------------------------------------------
# Variable
#
# Atributy a funkcionalita proměnné
# -----------------------------------------------------------
class Variable:
    def __init__(self, name):
        self.name = name
        self.v_type = None
        self.value = None

    # Změní u proměnné v_type a value
    def update(self, new_value, v_type):
        self.v_type = v_type
        self.value = new_value


# -----------------------------------------------------------
# Stack
#
# Metody pro práci se zásobníkem
# -----------------------------------------------------------
class Stack:
    def __init__(self):
        self.data = []
        self.top = None

    # Přidá data do zásobníku
    def push_stack(self, value):
        self.data.append(value)
        self.top = value

    # Vymaže data ze zásobníku
    def pop_stack(self):
        temp = self.data.pop()
        if len(self.data) > 0:
            self.top = self.data[len(self.data) - 1]
        else:
            self.top = None
        return temp

    # Vrátí vrchol zásobníku
    def get_top(self):
        if self.top is None:
            exit(ERROR_54)
        return self.top

    # Vrátí vrchní dvě položky ze zásobníku
    def get_tops(self):
        if len(self.data) < 2:
            exit(ERROR_54)
        return self.data[len(self.data) - 2], self.data[len(self.data) - 1]

    # Vymaže všechny data ze zásobníku
    def clear_stack(self):
        while self.top is not None:
            self.pop_stack()


def main():
    program = Interpret()
    program.arguments_validator.get_arguments()
    program.iterator()
    exit(ERROR_0)


if __name__ == '__main__':
    main()
