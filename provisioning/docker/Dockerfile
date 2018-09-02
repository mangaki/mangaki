FROM circleci/python:3.6-stretch-browsers

RUN sudo pip install --upgrade pip
RUN sudo pip install ansible
RUN mkdir -p ~/.ssh
RUN ssh-keyscan beta.mangaki.fr >> ~/.ssh/known_hosts
