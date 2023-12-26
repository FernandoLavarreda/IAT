#Excecute tests for compare_interest.py
#Fernando Lavarreda

import pytest
import compare_interests as cpi


def test_input_files():
    """Evaluate correct number of lines from multiple files"""
    files = ("tests/t1", "tests/t2")
    real_lines = 0
    for file in files:
        with open(file) as f:
            real_lines+=sum([1 for line in f.readlines() if len(line) and line[0]!="#"])
    read = cpi.read("tests/t1")+cpi.read("tests/t2")
    assert real_lines == len(read)


def test_compound():
    """Determine values computed are accurate"""
    lines = cpi.read("tests/t1")
    results = [cpi.process(line.split()) for line in lines]
    factor = (1+0.01)**(365/30)
    additions_last = 600*(1+0.02*90/365)*(1+0.02*90/365)
    values = (30e3*(1+0.02*90/365)**4, 30e3*(1+0.025*180/365)**2, (30e3*(1+0.025*180/365)+5000)*(1+0.025*180/365),
              (((30e3*(1+0.014*90/365)+2500)*(1+0.014*90/365)+1500)*(1+0.014*90/365)+700)*(1+0.014*90/365),
              30e3*(1+0.025),
              (((((((12e3*factor)+1500)*factor+2e3)*factor+300)*factor+900)*factor+800)*factor),
              (((additions_last+1e4*(1+0.04*180/365))*(1+0.04*180/365)+additions_last)*(1+0.04*180/365)+additions_last)*(1+0.04*180/365),
              ) #Expected final values
    expected = (cpi.Result(per_returned=(values[0]-30e3)/30e3, utility=values[0]-30e3, net_investment=30e3, increments=[values[0],], net_deposits=[30e3,0,0,0], effective_period="", name=""), 
                cpi.Result(per_returned=(values[1]-30e3)/30e3, utility=values[1]-30e3, net_investment=30e3, increments=[values[1],], net_deposits=[30e3,0], effective_period="", name=""),
                cpi.Result(per_returned=(values[2]-35e3)/35e3, utility=values[2]-35e3, net_investment=35e3, increments=[values[2],], net_deposits=[30e3,5e3], effective_period="", name=""),
                cpi.Result(per_returned=(values[3]-34700)/34700, utility=values[3]-34700, net_investment=34700, increments=[values[3],], net_deposits=[30e3,2500,1500,700], effective_period="", name=""),
                cpi.Result(per_returned=(values[4]-30e3)/30e3, utility=values[4]-30e3, net_investment=30e3, increments=[values[4],], net_deposits=[30e3], effective_period="", name=""),
                cpi.Result(per_returned=(values[5]-17500)/17500, utility=values[5]-17500, net_investment=17500, increments=[values[5],], net_deposits=[12000,1500, 2e3, 300, 900, 800],\
                           effective_period="", name=""),
                cpi.Result(per_returned=(values[6]-11800)/11800, utility=values[6]-11800, net_investment=11800, increments=[values[6],],\
                           effective_period="", net_deposits=[10000, 600, 0, 600, 0, 600, 0], name=""), #Because of the expansion a deposit for sub account will appear
                ) 
    assert len(expected) == len(lines)
    for i, exp in enumerate(expected):
        assert exp.net_deposits == pytest.approx(results[i].net_deposits)
        assert exp.per_returned == pytest.approx(results[i].per_returned)
        assert exp.increments[-1] == pytest.approx(results[i].increments[-1])


def test_synonyms():
    """Determine if equivalent expresions are parsed correctly"""
    lines = cpi.read("tests/t2")
    results = [cpi.process(line.split()) for line in lines]
    for result in results[:-1]:
        assert result.increments[-1] == pytest.approx(results[-1].increments[-1])


def test_exceptions():
    read = cpi.read("tests/e1")
    for line in read:
        with pytest.raises(ValueError):
            cpi.process(line.split())

