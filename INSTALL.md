# Installation

There are multiple ways to install ifsbench:
- via `pip install` as a pure Python package
- via CMake/ecbuild to enable installation as part of a CMake project
- manually

## Requirements

- Python 3.8+ with virtualenv and pip

## Installation without prior download

The easiest way to obtain a useable installation of > with the fparser frontend does not
require downloading the source code. Simply run the following commands:

```bash
python3 -m venv ifsbench_env  # Create a virtual environment
source ifsbench_env/bin/activate  # Activate the virtual environment

# Installation of the ifsbench core library
pip install "ifsbench @ git+https://github.com/ecmwf-ifs/ifsbench.git"
```

This makes the Python package available and installs the scripts `ifs-bench.py` script.


## Installation from source

After downloading the source code, e.g., via

```bash
git clone https://github.com/ecmwf-ifs/ifsbench.git
```

enter the created source directory and choose one of the following installation methods.

### Installation with pip

```bash
python3 -m venv ifsbench_env  # Create a virtual environment
source ifsbench_env/bin/activate  # Activate the virtual environment

# Installation of the ifsbench core library
# Optional:
#   * Add `-e` to obtain an editable install that allows modifying the
#     source files without having to re-install the package
#   * Enable the following options by providing them as a comma-separated
#     list in square brackets behind the `.`:
#     * tests    - allows running the ifsbench test suite
#     * grib     - installs dependencies to read/modify GRIB files
pip install .
```

### Installation using CMake/ecbuild

ifsbench can be installed using [ecbuild](https://github.com/ecmwf/ecbuild) (a set of CMake macros and a wrapper around CMake). This requires ecbuild 3.4+ and CMake 3.17+.

```bash
ecbuild <path-to-ifsbench>
make
```

The following options are available and can be enabled/disabled by providing `-DENABLE_<feature>=<ON|OFF>`:

- `EDITABLE` (default: `OFF`): Install ifsbench in editable mode, i.e. without
  copying any files
- `GRIB` (default: `OFF`): Install additional libraries that are required for 
  reading/ modifying GRIB files.

This method is also suitable to create a system-wide installation of ifsbench:

```bash
mkdir build && cd build
ecbuild --prefix=<install-path> <path-to-ifsbench>
make install
```

The ecbuild installation method creates a virtual environment in the build
directory.

## Installation as part of an ecbundle bundle

ifsbench being installable by CMake/ecbuild makes it easy to integrate with
[ecbundle](https://github.com/ecmwf/ecbundle). Simply add the following to your
`bundle.yml`:

```yaml
projects :

  # ...other projects ...

  - ifsbench :
    git     : https://github.com/ecmwf-ifs/ifsbench
    version : main

```

See the [CLOUDSC dwarf](https://github.com/ecmwf-ifs/dwarf-p-cloudsc) for an
example how this can be used.

## Manual installation

The following outlines the manual steps for installing ifsbench using a virtual
environment. This installation method is not recommended but may be used when
maximum control over all steps is required or all of the above are not working.
You can create an empty directory and copy-paste the following steps to obtain a
working version:

### 1. Clone the ifsbench repository

```bash
git clone https://github.com/ecmwf-ifs/ifsbench
```

### 2. Create and activate virtual environment

```bash
python3 -m venv ifsbench_env
source ifsbench_env/bin/activate
pip install --upgrade pip
```

Note that we need to make sure that we use a recent pip version (21.3 or newer)
that has support for editable installs using `pyproject.toml`.

### 3.  Install ifsbench and Python dependencies

```bash
cd ifsbench
pip install -e .[tests]
```


### 4.  Verify everything is working

```bash
py.test .
```