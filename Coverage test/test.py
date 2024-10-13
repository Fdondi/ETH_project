import pysnooper

from sum import sum, sum_only_positive

def test_sum():
    assert sum(5, 5) == 10

@pysnooper.snoop('snooptest1.log', depth=50)
def test_sum_positive_ok():
    assert sum_only_positive(2, 2) == 4

@pysnooper.snoop('snooptest2.log', depth=50)
def test_sum_positive_fail():
    assert sum_only_positive(-1, 2) is None