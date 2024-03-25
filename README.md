## IFSBench - A pythonic benchmarking package for IFS development

**NOTE**: _This is work-in-progress and represents a prototype, not a full solution!_

IFSBench is a prototype tool that aims to bring the RAPS-like ease of
testing and performance benchmarking for a select set of tests into
the bundle-based day-to-day IFS development workflow. It's basic
conceptual idea is equivalent to the current `ifs-test` suite, but it
is based on Python wrapper classes and tools to create a set of
lightweight benchmark scripts that provide additional features and a
more "pythonic" flavour of tooling. The primary planned features are:

* Configurable per-test benchmark scripts with an improved CLI
  (command-line interface).
* Reference benchmark results are processed as pandas.DataFrame
  objects and can be stored (and thus version-controlled) in a variety
  of light-weight formats (eg, .csv) without the need for complete log
  files.
* Large benchmark setups (eg. tl159-fc or tco399-fc) that can symlink,
  copy or download necessary input data from pre-defined locations and
  thus do not need git(-lfs) or cmake-based symlinking at configure
  time.
* Ability to parse DrHook profiles (thanks to Iain Miller!) into
  commonly accessible formats (again based on pandas.DataFrames), as
  well as the traditional test-based output format.

#### Installation

#### Examples

#### Coding style

The code should be checked with pylint in order to conform with the standards
specified in `.pylintrc`:
```
<build_dir>/ifsbench_env/bin/pylint --rcfile=.pylintrc ifsbench/ scripts/ tests/
```
