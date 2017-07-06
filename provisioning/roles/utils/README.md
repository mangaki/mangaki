# Utility roles

This directory contains a collection of Ansible roles for various third-party
services that are used by Mangaki. They are written to be fairly reusable and
generally won't have any specific dependencies on Mangaki itself (except that
they may not support much more options than those that are required for
Mangaki).

There are two types of roles in this directory that have slightly different
usage patterns.

## Program roles

These roles (`nginx`, `dehydrated`, etc.) set up a particular program that can
be used repeatedly through a site role (see below). They usually require
minimal configuration and should only be included once, since they will usually
install and configure a system-wide program.

## Site roles

These roles, whose name usually ends with `_site`, configure a program to serve
a particular resource. They can usually be reused several times in the same
playbook without trouble, and expose `allow_duplicates: true`.
