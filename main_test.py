#Excecute tests for compare_interest.py
#Fernando Lavarreda

import pytest
import compare_interests as cpi


def test_compund():
    """Test compound interest formula"""
    assert cpi.compound_interest(deposits=[1e3, 1e3, 1e3], rate=0.0456)[-1] == pytest.approx(((1e3*(1+0.0456)+1e3)*(1+0.0456)+1e3)*(1+0.0456))
    assert cpi.compound_interest(deposits=[2350, 0, 0], rate=0.0275)[-1] == pytest.approx(2350*(1+0.0275)**3)
    assert cpi.compound_interest(deposits=[0, 1e4, 0], rate=0.0389)[-1] == pytest.approx((1e4*(1+0.0389)**2))


def test_rate():
    """Read rate and parse rate"""
    assert cpi.parse_rate("0.0354:Y")[0] == pytest.approx(0.0354)
    assert cpi.parse_rate("0.0354:Y")[1] == cpi.Period.YEAR
    assert cpi.parse_rate("0.0673:Y:S")[0] == pytest.approx(0.0673)
    assert cpi.parse_rate("0.0673:Y:S")[2] == cpi.Period.SEMESTER


def test_compute_rate():
    """Process actual rate"""
    assert cpi.compute_rate_period(0.0354, cpi.Period.SEMESTER, None)[0] == pytest.approx(0.0354)
    assert cpi.compute_rate_period(0.0354, cpi.Period.SEMESTER, None)[1] == cpi.Period.SEMESTER
    assert cpi.compute_rate_period(0.0354, cpi.Period.SEMESTER, cpi.Period.DAY)[0] == pytest.approx(0.0354*cpi.Period.DAY.value/cpi.Period.SEMESTER.value)
    assert cpi.compute_rate_period(0.0354, cpi.Period.SEMESTER, cpi.Period.DAY)[1] == cpi.Period.DAY
    assert cpi.compute_rate_period(0.0791, cpi.Period.MONTH, cpi.Period.ZEAR)[0] == pytest.approx((1+0.0791)**(cpi.Period.ZEAR.value/cpi.Period.MONTH.value)-1)


def test_deposits():
    """Test parse and compute deposits"""
    assert cpi.parse_deposits("1000:12000:1350", sep="%")[1] == pytest.approx([1000,12000,1350])
    assert cpi.parse_deposits("1000:12000:1350", sep="%")[2] == False
    assert cpi.parse_deposits("1000:fill", sep="%")[2] == True
    assert cpi.parse_deposits("12000%0.02:Y%100:352:450", sep="%")[1] == pytest.approx(12000)
    assert cpi.parse_deposits("12000%0.02:Y%100:352:450", sep="%")[2] == pytest.approx([100, 352, 450])
    assert cpi.parse_deposits("12000%0.02:Y%100:352:450", sep="%")[3] == False
    assert cpi.parse_deposits("12000%0.02:Y%100:352:450", sep="%")[4] == pytest.approx(0.02)
    assert cpi.parse_deposits("12000%0.02:Y%100:352:450", sep="%")[5] == cpi.Period.YEAR


def test_compute_deposit_lists():
    """Test lists"""
    assert cpi.compute_deposits_list1([12, 12, 12], False, 3) == pytest.approx([12, 12, 12])
    assert cpi.compute_deposits_list1([15, 46, 78, 98], False, 6) == pytest.approx([15, 46, 78, 98, 0, 0])
    assert cpi.compute_deposits_list1([15, 88, 99], True, 7) == pytest.approx([15, 88, 99, 99, 99, 99, 99])


def test_time():
    """Parse time"""
    assert cpi.parse_time("12:S")[0] == pytest.approx(12)
    assert cpi.parse_time("12:S")[1] == cpi.Period.SEMESTER


def test_input_files():
    """Evaluate correct number of lines from multiple files"""
    files = ("tests/t1", "tests/t2")
    real_lines = 0
    for file in files:
        with open(file) as f:
            real_lines+=sum([1 for line in f.readlines() if len(line) and line[0]!="#"])
    read = cpi.read("tests/t1")+cpi.read("tests/t2")
    assert real_lines == len(read)


def test_process():
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

