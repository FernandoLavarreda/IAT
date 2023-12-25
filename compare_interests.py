#!./venv/bin/python3
#Fernando Lavarreda
import traceback
import re
import os.path
from enum import Enum
from inspect import signature
from rich.table import Table
from rich.console import Console
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Callable, Tuple


COMMANDS = {}

@dataclass
class Command:
    id:int
    name:str
    desc:str
    func:Callable
    required:bool


def command(name:str, required:bool=False, alias:str=""):
    def build_command(func:Callable):
        def wrapper(*args, **kwargs):
            sg = list(signature(func).parameters.values())
            if len(sg)>len(args)+sum([type(v.default)!=type for v in sg]):
                print("Incorrect number of parameters for "+name)
                print(func.__doc__)
                return
            return func(*args, **kwargs)
        assert name not in COMMANDS, "Name "+name+"  has already been added to commands"
        cmd = Command(len(COMMANDS), name, func.__doc__, wrapper, required)
        COMMANDS[name] = cmd 
        if alias:
            assert alias not in COMMANDS, "Alias "+alias+" has already been added to commands"
            COMMANDS[alias] = cmd 
        return wrapper
    return build_command


class Period(Enum):
    """Specify periods in days"""
    DAY=1
    MONTH=30
    BIMESTER=60
    TRIMESTER=90
    QUADMESTER=120
    SEMESTER=180
    YEAR=365
    ZEAR=730


ALIASES = {
          Period.DAY:("D", "DAY", "1"),
          Period.MONTH:("M", "", "30"),
          Period.BIMESTER:("B", "BIMESTER", "60"),
          Period.TRIMESTER:("T", "TRIMESTER", "90"),
          Period.QUADMESTER:("Q", "QUADMESTER", "120"),
          Period.SEMESTER:("S", "SEMESTER", "180"),
          Period.YEAR:("Y", "YEAR", "365"),
          Period.ZEAR:("Z", "ZEAR", "730"),
          }


def compound_interest(deposits:list[float], rate:float)->list[float]:
    """Compound interest of a series of deposits. Each deposit represents a period to generate interest.
       The rate should represent the effective rate for each period. The first deposit is interpreted as
       the starting capital. Returning a list that has a length len(deposits)+1 where 0th is the initial
       balance.
    """
    balance = [] 
    if not deposits:
        return balance
    balance.append(deposits[0])
    for deposit in deposits:
        if len(balance)>1:
            p = (balance[-1]+deposit)*(1+rate)
        else:
            p = deposit*(1+rate)
        balance.append(p)
    return balance


@command(name='-r', alias='--rate', required=True)
def parse_rate(command:str):
    """Process interest rate of an entry:
       
       Expected patterns:
        - float:Period
        - float:Period:Period
       
       Example:
        --rate 0.02:Y:T
        This means that the rate is 2% annually but the period of composition is each trimester so
        the interest will be 90/365*0.02
        If the second option is greater the effective rate is (1+rate)^(second/first)
    """
    tokens = command.split(":")
    assert len(tokens)<=3, "Rate must be either float:Period or float:Period:Period" 
    try:
        rate = float(tokens[0])
    except ValueError:
       raise ValueError("Rate must be a real number")
    start_end = [None, None]
    for i, t in enumerate(tokens[1:]):
        for k, v in ALIASES.items():
            if t in v:
                start_end[i] = k
                break
    if start_end.count(None)+len(tokens)!=3:
        raise ValueError("Invalid parameter for rate: ", tokens[1:])
    return rate, *start_end


def compute_rate_period(rate:float, start:Period, end:Period):
    """Obtain effective rate, if there is no end period effective rate is the input and capitalization period is start.
       If end is greater than start effective rate is (1+r)^n where n is end/start.
       If second is smaller the effective rate is proportional to the original value r*end/start
    """
    if end:
        if end.value>start.value:
            return (1+rate)**(end.value/start.value)-1, end
        else:
            return rate*end.value/start.value, end
    return rate, start


@command(name='-d', alias='--deposits', required=True)
def parse_deposits(command:str, sep:str="%"):
    """Parse series of deposits for interest analysis

    Option 1: Read the simple deposits to be added to the compound interest analysis.
        
        Expected paterns lists of deposits (floats):
         - deposit1:deposit2:deposit3:...
         - deposit1:fill
        Where 'fill' will be used to fill missing gaps with the last value of the list
        
        Example:
         --deposits 12000:1000:fill
         This means that the initial balance is 12k followed by deposits of 1k for each
         period

    Option 2: Create a series of deposits with an initial balance + interest generated from
              another source (i.e an account that generates interest Trimester -> transfer all to a Yearly)
       
        Expected pattern:
         - balance%rate_pattern%deposit_pattern
        Example:
         --deposits 12000%0.02:Y:T%12000:1000:fill
         This means have an initial balance of 12k that will have added the results from a Trimester 2% Year account
         Take into account that the main account (12k) will have added the result of its_period//trimester.
         The period is defined in the parameter --rate. So the secondary account may earn interests twice if the main
         one has a SEMESTER period or four if it has a YEAR period. Bear in mind that period//trimester should be positive
         otherwise there is no value to add. (Second account is emptied each time)

        Where balance is the initial balance for the main account, rate_pattern (see --help rate)
        specifies the rate for the short term account and deposit_patter (see --help deposit) are
        the deposits to the short term account
    """
    parsed = (0, *parse_deposits1(command)) if sep not in command else (1, *parse_deposits2(command))
    return parsed 

def parse_deposits1(command:str):
    tokens = command.split(":")
    parsed_tokens = []
    fill = -1 if "fill" == tokens[-1] else len(tokens)
    for t in tokens[:fill]:
        try:
            parsed_tokens.append(float(t))
        except ValueError:
            raise ValueError("Deposit: "+t+ " could not be interpreted")
    return parsed_tokens, fill==-1


def parse_deposits2(command:str, sep:str="%"):
    parse = command.split(sep)
    if len(parse)!=3:
        raise ValueError("Could not parse deposit pattern "+command)
    balance, rate, deposits = parse 
    try:
        balance = float(balance)
    except ValueError as e:
        raise ValueError("Could not interpret balance: "+balance)
    try:
        rate, start, end = parse_rate(rate)
        eff_rate, eff_period = compute_rate_period(rate, start, end)
    except ValueError as e:
        raise ValueError("Could not interpret rate inside deposits: \n"+str(e))
    try:
        parsed_tokens, fill = parse_deposits1(deposits)
    except ValueError as e:
        raise ValueError("Could not interpret deposit for rate assigned in deposits:\n"+str(e))
    return balance, parsed_tokens, fill, eff_rate, eff_period
    

def compute_deposits_list1(deposits:list[float], fill:bool, periods:int):
    """Create list of deposits the number of periods must be an integer.
      If the deposits excede the number of periods deposits are dropped.
      If they are less they are filled with 0s unless the parameter fill
      is set to True which indicates that missing values should be filled
      with the las entry.
    """
    if len(deposits)>= periods:
        return deposits[:periods]
    filler = deposits[-1] if fill else 0
    return deposits+[filler for i in range(periods-len(deposits))]


def compute_deposits_list2(balance:float, deposits:list[float], fill:bool, eff_rate:float, eff_period:Period, period:Period, periods:int):
    """Create list of deposits as the result of another compound interest analysis.
       Imagine an account that generates interest every Year and an account that
       generates every Trimester. Now what if you would invest in the latter and
       when a Year ends you empty this account and move the money to the former?
       This is an optimal strategy assuming that there is money idling and the
       Year account is closed (meaning you can't keep depositing until the period ends).
       Ideally the Year account/deposit should have a better interest as well
    """
    assert period.value//eff_period.value, "No interest will be generated for the deposits since "+str(eff_period)+">"+str(period)
    net_deposits = compute_deposits_list1(deposits, fill, period.value//eff_period.value)
    actual_deposit = compound_interest(net_deposits, eff_rate)[-1] #The last balance from the compound interest is what will be invested
    return [balance,]+[actual_deposit]*(periods-1), [balance,]+net_deposits*(periods-1)



@command(name='-t', alias='--time', required=True)
def parse_time(command:str):
    """Interpret the time where the analysis should be done

        Expected input:
         - int:Period

        Example:
         --time 14:Y
         This means 14 years for the analysis
    """
    tokens = command.split(":")
    assert len(tokens)==2, "Must provide nperiods:Period to determine time scope of analysis"
    try:
        nunits = int(tokens[0])
    except ValueError:
        raise ValueError("Could not interpret units for the time scope (must be int), given "+tokens[0])
    unit = None
    for k, v in ALIASES.items():
        if tokens[1] in v:
            unit = k
            break
    if not unit:
        raise ValueError("Could not interpret unit: "+token[1])
    return nunits, unit 



def read_args(args:list[str]):
    """Process arguments and flags sent to program
       Converts aliases to names"""
    max_id = max([cmd.id for cmd in COMMANDS.values()]) 
    mask = [1 for i in range(max_id+1)]
    behavior = {}
    last_added = ""
    for arg in args:
        if arg in COMMANDS:
            behavior[COMMANDS[arg].name] = []
            mask[COMMANDS[arg].id] = 0
            last_added = COMMANDS[arg].name
        else:
            if last_added:
                behavior[last_added].append(arg)
            else:
                raise ValueError("Unrecognized command "+arg)
    if "-i" in behavior and behavior["-i"] or "-h" in behavior:
        return behavior
    for k, cmd in COMMANDS.items():
        if cmd.required and mask[cmd.id]:
            raise ValueError("Missing command: "+k+"\n"+cmd.name)
    return behavior

@command(name="-i", required=False, alias="--input")
def read(buf:str):   
    """Get input from a file or from stdin, a file is read until EOF
       each line must be a valid command. If no argument is provided
       it is assumed that assummed stdin which is read until a single
       's' is entered
        
        Example:
         --input rs.txt
    """
    feed = []
    stop = "n"
    if buf:
        if not os.path.isfile(buf):
            raise ValueError(buf+" is not a file")
        file = open(buf)
        feed = file.readlines()
        file.close()
        stop = ""
    while stop:
        stop = input()
        if stop!="s":
            feed.append(stop)
        else:
            break
    return feed


@dataclass
class Result:
    per_returned:float
    utility:float
    net_investment:float
    increments:list[float]
    effective_deposits:list[float]
    effective_period:Period
    name:str


def stats(increments, net_deposits)->list[float]:
    """Compute total invested, utilities, %returned"""
    net_investment = sum(net_deposits)
    utility = increments[-1]-net_investment
    per_returned = utility/net_investment
    return per_returned, utility, net_investment


def process(args:list[str])->Result:
    """Process a single line, does not process --input flag nor --graph"""
    try:
        init = {}
        mask = read_args(args)
        for k, v in mask.items():
            if COMMANDS[k].required:
                init[k] = COMMANDS[k].func(*v)
        if None in init.values(): 
            raise ValueError("Missing arguments")
        initial_rate, start, end = init["-r"]
        compound_deposits, *parsed_deposits = init["-d"]
        nunits, unit_time = init["-t"]
        effective_rate, effective_period = compute_rate_period(initial_rate, start, end)
        if compound_deposits:
            effective_deposits, net_deposits = compute_deposits_list2(*parsed_deposits, effective_period, nunits*unit_time.value//effective_period.value)
        else:
            effective_deposits = compute_deposits_list1(*parsed_deposits, nunits*unit_time.value//effective_period.value)
            net_deposits = effective_deposits
        increments = compound_interest(effective_deposits, effective_rate)
        name = mask["-n"][0] if "-n" in mask and len(mask["-n"]) else ALIASES[effective_period][0]+"-"+str(initial_rate)+"%"
        result = Result(*stats(increments, net_deposits), increments, net_deposits, effective_period,\
                        name=name)
        return result
    except ValueError:
        return None
    except Exception as e:
        print(e)


@command(name="-n", required=False, alias="--name")
def name(n:str):
    """Provide a name to an analysis to make comparisons easier.
       Default name:
        - Period-nominal_rate
    """
    return n


@command(name="-s", required=False, alias="--sort")
def sort_results(field:str)->int:
    """Sort results based on the desired field
       Accepeted values: 
        - R: %Returned)
        - U: Utility
        - T: Total returned
        - N: Net investment
    """
    fields = ["R", "U", "T", "N"]
    try:
        f = fields.index(field)
    except ValueError:
        raise ValueError("Invalid argument for sorting "+field)
    return f


@command(name="-o", required=False, alias="--output")
def write(buf:str):
    """Direct results to stdout or to a file. If no output is
       selected stdout will be assumed.
       
       Example:
        --output fout.txt
    """
    return buf


def write_file(buf:str, results:list[Result]):
    try:
        with open(buf, "w") as fd:
            for i, result in enumerate(results):
                fd.write(str(i)+"|"+result.name+"|"+str(result.per_returned*100)+"|"+str(result.utility)+"|"+\
                         str(result.increments[-1])+"|"+str(result.net_investment)+"\n")
    except Exception as e:
        raise ValueError("Could not write file: "+buf)


def write_console(results:list[Result]):
    columns = ("ID", "Name", "% Returned", "Utility", "Total", "Net Investment")
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    for column in columns:
        table.add_column(column)
    for i, result in enumerate(results):
        table.add_row("[red]"+str(i)+"[/red]", "[#db7c07]"+result.name+"[/#db7c07]","[green]"+str(result.per_returned*100)+"[/green]", "[blue]"+str(result.utility)+"[/blue]",\
                      "[white]"+str(result.increments[-1])+"[/white]","[bold]"+str(result.net_investment)+"[/bold]")
    console.print(table)

@command(name="-g", required=False, alias="--graph")
def parse_graph(base:Period):
    """Graph results through time, x axis must be a valid Period
        
        Example:
         --graph Y
         This means that x axis will be in years.
    """
    for k,v in ALIASES.items():
        if base in v:
            return k
    raise ValueError("Could not interpret period "+base)


def graph(results:list[Result], base:Period):
    """Graph results through time""" 
    for i, r in enumerate(results):
        plt.plot([i*r.effective_period.value/base.value for i in range(len(r.increments))], r.increments, label=f"Results: {i}")
    plt.legend()
    plt.show()


@command(name="-h", required=False, alias="--help")
def help(command:str):
    """
*********************************************************************************|
Pogram designed to analyze different compound interest scenarios.                |
By: Fernando Lavarreda                                                           |
*********************************************************************************|
                                                                                 |
       To see particular command type --help command                             |
                                                                                 |
        Example usage:                                                           |
         ./compare_interests.py --rate 0.02:Y --deposits 10000:fill --time 2:Y   |
                                                                                 |
---------------------------------------------------------------------------------*"""
    req = "--"+command if "--"+command in COMMANDS else "-"+command
    if req in COMMANDS:
        print(COMMANDS[req].desc)
        return 0
    if req.strip()!="-":
        print("Command "+command+" not recognized")
        return 0
    print(COMMANDS["-h"].desc)
    seen = [COMMANDS["-h"].id,]
    for c, v in COMMANDS.items():
        if "--" in c and v.id not in seen:
            print(v.desc)
            seen.append(v.id)
    for c, v in COMMANDS.items():
        if "-" in c and v.id not in seen:
            print(v.desc)
            seen.append(v.id)
    return 0


def main(args:list[str]):
    try:
        mask = read_args(args)
        results = []
        if "-h" in mask:
            inp = mask["-h"][0] if mask["-h"] else ""
            COMMANDS["-h"].func(inp)
            return
        if "-i" not in mask or not mask["-i"]:
            print("Enter 's' to stop adding analysis")
            feed = read("")
            feed.append(" ".join(args))
        else:
            feed = []
            for f in mask["-i"]:
                feed += read(f)
        for n in feed:
            r = process(n.split())
            if r:
                results.append(r)
        if "-s" in mask and mask["-s"]:
            i = COMMANDS["-s"].func(*mask["-s"])
            match i:
                case 0:
                    results.sort(key=lambda x: x.per_returned)
                case 1:
                    results.sort(key=lambda x: x.utility)
                case 2:
                    results.sort(key=lambda x: x.increments[-1])
                case 3:
                    results.sort(key=lambda x: x.net_investment)
            results = results[::-1]
        if "-o" not in mask or not mask["-o"]:
            if results:
                write_console(results)
        else:
            write_file(mask["-o"][0], results)
        if "-g" in mask and results:
            base = parse_graph(*mask["-g"])
            if base:
                graph(results, base)

    except Exception as e:
        print(str(e))
        return 1
    return 0


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])


