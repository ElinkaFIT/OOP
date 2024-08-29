<?php
ini_set('display_errors', 'stderr');

const OK = 0;
const ERR_ARG = 10;
const ERR_CODE21 = 21;
const ERR_CODE22 = 22;
const ERR_CODE23= 23;

$ippcode23 = false;
$instr_order = 1;
 
function help_arg($argc, $argv){
    
    if($argc > 1){
        if($argv[1] == "--help"){
            if ($argc == 2){
                echo ("SYNOPSIS: php8.1 parser.php [OPTION]... [FILE]\n");
                exit (OK);
            }
            else{
                exit (ERR_ARG);
            }
        }
    } 

}

function zero_arg_xml($xw, $instr){
    global $instr_order;
    xmlwriter_start_element($xw, 'instruction');

    xmlwriter_start_attribute($xw, 'order');
    xmlwriter_text($xw, $instr_order);
    xmlwriter_end_attribute($xw);

    xmlwriter_start_attribute($xw, 'opcode');
    xmlwriter_text($xw, strtoupper($instr));
    xmlwriter_end_attribute($xw);

    $instr_order++;
}

function arg_var_xml($xw, $variable, $position){
    $var_match = preg_match('/^[GTL]F@(?:[a-zA-Z]|[_\-$&%*!?])(?:\w|[_\-$&%*!?])*$/', $variable);
    if ($var_match == 0){
        exit (ERR_CODE23);
    }
    xmlwriter_start_element($xw, 'arg' . $position);

    xmlwriter_start_attribute($xw, 'type');
    xmlwriter_text($xw, 'var');
    xmlwriter_end_attribute($xw);

    xmlwriter_text($xw, $variable);

    xmlwriter_end_element($xw);
}

function arg_label_xml($xw, $label, $position){
    $lab_match = preg_match('/(?:^[a-zA-Z]|[_\-$&%*!?])(?:\w|[_\-$&%*!?])*$/', $label);
    if ($lab_match == 0){
        exit (ERR_CODE23);
    }

    xmlwriter_start_element($xw, 'arg' . $position);

    xmlwriter_start_attribute($xw, 'type');
    xmlwriter_text($xw, 'label');
    xmlwriter_end_attribute($xw);

    xmlwriter_text($xw, $label);

    xmlwriter_end_element($xw);
}

function arg_symb_xml($xw, $splitline, $position){
    $symb_match = preg_match('/.+@.*/', $splitline);
    if ($symb_match == 0){
        exit (ERR_CODE23);
    }
    // rozdeleni casti
    $symb = explode("@", $splitline);
    if(count($symb) != 2){
        exit (ERR_CODE23);
    }
    if ($symb[0] == "nil" | $symb[0] == "int" | $symb[0] == "bool" | $symb[0] == "string"){
        switch ($symb[0]) {
            case 'nil':
                if ($symb[1] != "nil" & $symb[1] != ""){
                    exit (ERR_CODE23);
                }
                break;
            case 'bool':
                if ($symb[1] != "true" & $symb[1] != "false" & $symb[1] != ""){
                    exit (ERR_CODE23);
                }
                break;
            case 'int':
                $int_match = preg_match('/^(?:[\-\+])?(?:0[xX][\da-fA-F]+|0[oO]0-7]+|\d+)$/', $symb[1]);
                if ($int_match == 0 | $symb[1] == ""){
                    exit (ERR_CODE23);
                }
                break;
            case 'string':
                $re = '/^(?:[^\\\\#\s]|(?:\\\\\d\d\d))*$/';
                $str_match = preg_match($re, $symb[1]);
                if ($str_match == 0){
                    exit (ERR_CODE23);
                }
                break;
            default:
                break;
        }
        
        xmlwriter_start_element($xw, 'arg' . $position);

        xmlwriter_start_attribute($xw, 'type');

        xmlwriter_text($xw, $symb[0]);
        xmlwriter_end_attribute($xw);

        xmlwriter_text($xw, $symb[1]);

        xmlwriter_end_element($xw);
    }
    else{
        arg_var_xml($xw, $splitline, $position);
    }

}

function main($argc, $argv){
    global $ippcode23;
    global $instr_order;

    help_arg($argc, $argv);

    // create xml document
    $xw = xmlwriter_open_memory();
    xmlwriter_set_indent($xw, 1);

    xmlwriter_start_document($xw, '1.0', 'UTF-8');

    while ($line = fgets(STDIN)){

        // odstraneni komentare
        $line_len = strlen($line);
        for ($i=0; $i < $line_len; $i++) { 
            if($line[$i] == "#"){
                $line = strstr($line, "#", true);
                $line = $line . "\n";
                break;
            }
        }
        
        // rozkouskovani 
        $line = preg_replace('/[\t]|[ ]{2,}/', ' ', trim($line));
        $splitline = explode(' ', $line);
        
        
        // kontrola hlavicky
        if($ippcode23 == false){
            if(strtoupper($splitline[0]) == ".IPPCODE23" & count($splitline) == 1){
                xmlwriter_start_element($xw, 'program');
                xmlwriter_start_attribute($xw, 'language');
                xmlwriter_text($xw, 'IPPcode23');
                xmlwriter_end_attribute($xw);
                $ippcode23 = true;
                continue;
            }
            else if($splitline[0] != ""){
                exit (ERR_CODE21);
            }
        }

        switch (strtoupper($splitline[0])) {
            // 0 argumentu
            case 'CREATEFRAME':
            case 'PUSHFRAME':
            case 'POPFRAME':
            case 'RETURN':
            case 'BREAK':
                if(count($splitline) != 1){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                xmlwriter_end_element($xw);

                break;

            // 1 argumentu
            case 'DEFVAR':
            case 'POPS':
                if(count($splitline) != 2){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_var_xml($xw, $splitline[1], 1);

                xmlwriter_end_element($xw);
                break;

            case 'CALL':
            case 'LABEL':
            case 'JUMP':
                if(count($splitline) != 2){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_label_xml($xw, $splitline[1], 1);

                xmlwriter_end_element($xw);
                break;

            case 'PUSHS':
            case 'WRITE':
            case 'EXIT':
            case 'DPRINT':
                if(count($splitline) != 2){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_symb_xml($xw, $splitline[1], 1);

                xmlwriter_end_element($xw);
                break;
            
            // 2 argumenty
            case 'MOVE':
            case 'INT2CHAR':
            case 'STRLEN':
            case 'TYPE':
            case 'NOT':
                if(count($splitline) != 3){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_var_xml($xw, $splitline[1], 1);
                arg_symb_xml($xw, $splitline[2], 2);

                xmlwriter_end_element($xw);
                break;

            case 'READ':
                if(count($splitline) != 3){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_var_xml($xw, $splitline[1], 1);

                // type arg
                if ($splitline[2] != "nil" & $splitline[2] != "int" & $splitline[2] != "bool" & $splitline[2] != "string"){
                    exit (ERR_CODE23);
                }
                xmlwriter_start_element($xw, 'arg2');
                xmlwriter_start_attribute($xw, 'type');
                xmlwriter_text($xw, 'type');
                xmlwriter_end_attribute($xw);
                xmlwriter_text($xw, $splitline[2]);
                xmlwriter_end_element($xw);

                xmlwriter_end_element($xw);
                break;

            // 3 argumenty
            case 'ADD':
            case 'SUB':
            case 'MUL':
            case 'IDIV':
            case 'LT':
            case 'GT':
            case 'EQ':
            case 'AND': // ??
            case 'OR':
            case 'STRI2INT':
            case 'CONCAT':
            case 'GETCHAR':
            case 'SETCHAR':
                if(count($splitline) != 4){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_var_xml($xw, $splitline[1], 1);
                arg_symb_xml($xw, $splitline[2], 2);
                arg_symb_xml($xw, $splitline[3], 3);

                xmlwriter_end_element($xw);
                break;

            case 'JUMPIFEQ':
            case 'JUMPIFNEQ':
                if(count($splitline) != 4){
                    exit (ERR_CODE23);
                }
                zero_arg_xml($xw, $splitline[0]);
                arg_label_xml($xw, $splitline[1], 1);
                arg_symb_xml($xw, $splitline[2], 2);
                arg_symb_xml($xw, $splitline[3], 3);

                xmlwriter_end_element($xw);
                break;

            default:
                if (count($splitline) > 0 & $splitline[0] != "") {
                    exit (ERR_CODE22);  
                }
                break;
        }

    }
    xmlwriter_end_element($xw); 
    xmlwriter_end_document($xw);
    fwrite(STDOUT, xmlwriter_output_memory($xw));
    exit(OK);
    
}

main($argc, $argv);

?>