import re

import pytest
from rpmlint.checks.SpecCheck import SpecCheck
from rpmlint.filter import Filter

from Testing import CONFIG, get_tested_package, get_tested_spec_package


@pytest.fixture(scope='function', autouse=True)
def speccheck():
    CONFIG.info = True
    output = Filter(CONFIG)
    test = SpecCheck(CONFIG, output)
    return output, test


def test_check_include(tmpdir, speccheck):
    output, test = speccheck
    test.check_source(get_tested_package('source/CheckInclude', tmpdir))
    out = output.print_results(output.results)
    assert 'no-buildroot-tag' in out
    assert 'E: specfile-error error: query of specfile' not in out


@pytest.mark.parametrize('package', ['spec/SpecCheck2', 'spec/SpecCheck3'])
def test_patch_not_applied(package, speccheck):
    output, test = speccheck
    pkg = get_tested_spec_package(package)
    test.check_spec(pkg, pkg.name)
    out = output.print_results(output.results)
    assert 'patch-not-applied' not in out


@pytest.mark.parametrize('package', ['spec/SpecCheck'])
def test_distribution_tags(package, speccheck):
    output, test = speccheck
    pkg = get_tested_spec_package(package)
    test.check_spec(pkg, pkg.name)
    out = output.print_results(output.results)
    assert 'patch-not-applied Patch3' in out
    assert not re.search(r'patch-not-applied Patch\b', out)
    assert not re.search('patch-not-applied Patch[0124567]', out)
    assert 'libdir-macro-in-noarch-package' not in out
    assert len(re.findall('macro-in-comment', out)) == 1
    assert 'unversioned-explicit-provides unversioned-provides' in out
    assert 'unversioned-explicit-provides versioned-provides' not in out
    assert 'unversioned-explicit-provides /' not in out
    assert 'unversioned-explicit-obsoletes unversioned-obsoletes' in out
    assert 'unversioned-explicit-obsoletes versioned-obsoletes' not in out
    assert 'unversioned-explicit-obsoletes /' not in out
    assert 'setup-not-quiet' in out
