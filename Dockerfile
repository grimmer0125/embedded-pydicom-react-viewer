FROM ubuntu:20.04
# debian GNU/Linux 9 
# FROM node:15.14.0 

# Issue 1: no print anything. 
# Solution: https://stackoverflow.com/questions/64804749/docker-build-not-showing-any-output-from-commands
# RUN ls
# RUN echo $HOME

# RUN curl -sL https://deb.nodesource.com/setup_15.x | bash -
# 15.14+
# RUN apt-get install -y nodejs 
# ENV WORK_DIR /root/pyodide-reactapp
WORKDIR /root/pyodide_react_dicom_viewer

# replace shell with bash so we can source files
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN apt-get update
RUN apt-get install -y curl unzip git
# For python
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
RUN apt-get install -y --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 15.14.0
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash   

# Issue 2: seems "cd" not be inherited, 
# https://stackoverflow.com/questions/17891981/docker-run-cd-does-not-work-as-expected 
# RUN cd $HOME/.nvm 
# RUN cd ../nvm

# Issue 3 (nvm/node path): neither source ~/.bashrc or source $NVM_DIR/nvm.sh does work 
# Answer: https://stackoverflow.com/questions/25899912/how-to-install-nvm-in-docker

# ref: https://gist.github.com/remarkablemark/aacf14c29b3f01d6900d13137b21db3a
RUN source $NVM_DIR/nvm.sh && nvm install $NODE_VERSION
# add node and npm to path so the commands are available
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
# confirm installation
RUN node -v
RUN npm -v
RUN npm install --global yarn
RUN yarn set version berry

# RUN apt install -y software-properties-common
# RUN add-apt-repository -y ppa:deadsnakes/ppa
## it will install 3.9.4 
# RUN apt-get install -y python3.9 

ENV PYTHON_VERSION 3.9.2
# ref: https://gist.github.com/jprjr/7667947#gistcomment-3684823
# https://stackoverflow.com/questions/63230597/pyenv-unable-to-find-docker-compose
# Set-up necessary Env vars for PyEnv
ENV PYENV_ROOT /root/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
# Install pyenv, rehash is about shims & "pyenv init" will use it
RUN set -ex \
    && curl https://pyenv.run | bash \
    && pyenv update \
    && pyenv install $PYTHON_VERSION \
    && pyenv global $PYTHON_VERSION \
    && pyenv rehash

RUN echo "print python version"
RUN python --version

RUN echo "Install poetry"
# ref:
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker 
# Install and setup poetry
RUN pip install -U pip \
    && apt install -y netcat \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH="${PATH}:/root/.poetry/bin"

COPY . .
RUN sh ./download_pyodide.sh
RUN yarn install
RUN poetry install
RUN yarn build 

EXPOSE 8080
CMD [ "poetry", "run", "uvicorn", "--host", "0.0.0.0", "main:app"]










