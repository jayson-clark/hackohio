# 🔧 Installation Fix for Python 3.13

## Problem
You're using Python 3.13, which is too new! The `spacy` and `scispacy` libraries don't have pre-built wheels for Python 3.13 yet, causing compilation errors.

## ✅ Solution: Use Python 3.11 or 3.12

###Option 1: Using pyenv (Recommended)

```bash
# Install pyenv if you don't have it
brew install pyenv

# Install Python 3.12
pyenv install 3.12.0

# Set Python 3.12 for this project
cd /Users/jalenfrancis/calhacks/backend
pyenv local 3.12.0

# Recreate venv with Python 3.12
rm -rf venv
python -m venv venv
source venv/bin/activate

# Now install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install scispacy model
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

### Option 2: Using Homebrew Python

```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Navigate to backend
cd /Users/jalenfrancis/calhacks/backend

# Remove old venv
rm -rf venv

# Create new venv with Python 3.12
/opt/homebrew/bin/python3.12 -m venv venv
source venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.x

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install scispacy model
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

### Option 3: Quick Conda Setup

```bash
# Install miniforge if you don't have it
brew install miniforge

# Create conda environment with Python 3.12
conda create -n synapse python=3.12 -y
conda activate synapse

# Navigate to backend
cd /Users/jalenfrancis/calhacks/backend

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install scispacy model
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

## After Installation

Once you've successfully installed with Python 3.11/3.12:

```bash
# Test backend
cd backend
source venv/bin/activate  # or: conda activate synapse
python -m app.main

# In another terminal, test frontend
cd frontend
npm install
npm run dev
```

## Why This Happens

- **Python 3.13** was released in October 2024
- Scientific Python packages (numpy, scipy, spacy) take time to build wheels for new Python versions
- Python 3.11 and 3.12 have mature ecosystem support

## Check Your Python Version

```bash
python --version
```

If it shows 3.13.x, follow the steps above!

---

**After fixing:** Run the main `setup.sh` script again and it should work!

