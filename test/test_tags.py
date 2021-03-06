import pytest
from rpmlint.checks.TagsCheck import TagsCheck
from rpmlint.filter import Filter

from Testing import CONFIG, get_tested_package


@pytest.fixture(scope='function', autouse=True)
def tagscheck():
    CONFIG.info = True
    output = Filter(CONFIG)
    test = TagsCheck(CONFIG, output)
    return output, test


@pytest.mark.parametrize('package', ['binary/unexpanded1'])
def test_unexpanded_macros(tmpdir, package, tagscheck):
    output, test = tagscheck
    test.check(get_tested_package(package, tmpdir))
    out = output.print_results(output.results)
    assert 'unexpanded-macro Recommends' in out
    assert 'unexpanded-macro Provides' in out
    assert 'unexpanded-macro Conflicts' in out
    assert 'unexpanded-macro Suggests' in out
    assert 'unexpanded-macro Obsoletes' in out
    assert 'unexpanded-macro Enhances' in out
