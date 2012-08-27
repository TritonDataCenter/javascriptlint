BUILDOS=$(shell uname -s)
BUILDDIR = build
INSTALLDIRS =					\
	$(BUILDDIR)/install			\
	$(BUILDDIR)/install/javascriptlint	\

CSRCS = \
	nodepos.c		\
	pyspidermonkey.c

OBJECTS = $(CSRCS:%.c=$(BUILDDIR)/%.o)
CFLAGS += -fno-strict-aliasing -O -fPIC

SOLDFLAGS += -shared
CPPFLAGS += -DNDEBUG -D_REENTRANT					\
	-Ispidermonkey/src -Ispidermonkey/src/build			\
	-I/usr/include							\


ifeq ($(BUILDOS),Darwin)
	PY_PYTHON=$(shell python -c "import sys; print(sys.executable)")
	PY_PREFIX=$(shell $(PY_PYTHON) -c "import sys; print(sys.prefix)")
	PY_VERSION=$(shell $(PY_PYTHON) -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
	# Our best guess at the arch with which python will be launched.
	PY_ARCH=$(shell uname -m)
	CPPFLAGS += -I$(PY_PREFIX)/include/python$(PY_VERSION)
	SOLDFLAGS += $(PY_PREFIX)/Python
	LD=gcc -arch $(PY_ARCH)
	CC=gcc -arch $(PY_ARCH)
else
# This is known to work on 2.6 and 2.7.
	PY_PYTHON=$(shell python -c "import sys; print(sys.executable)")
	PY_PREFIX=$(shell $(PY_PYTHON) -c "import sys; print(sys.prefix)")
	PY_VERSION=$(shell $(PY_PYTHON) -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
	CPPFLAGS += -I$(PY_PREFIX)/include/python$(PY_VERSION)
endif

SOFILE = $(BUILDDIR)/pyspidermonkey.so

all: $(SOFILE)

$(BUILDDIR) $(INSTALLDIRS):
	mkdir -p $@

$(OBJECTS): spidermonkey/src/build/libjs.a spidermonkey/src/build/js_operating_system.h

$(SOFILE): $(OBJECTS)
	$(LD) $(SOLDFLAGS) $(LDFLAGS) $(OBJECTS) -Lspidermonkey/src/build -ljs -o $@

$(BUILDDIR)/%.o: javascriptlint/pyspidermonkey/%.c | $(BUILDDIR)
	$(CC) -o $@ -c $(CFLAGS) $(CPPFLAGS) $<

spidermonkey/src/build/libjs.a:
	(cd spidermonkey/src && CC="$(CC)" $(MAKE))

spidermonkey/src/build/js_operating_system.h:
	echo "#define XP_UNIX" > $@

clean:
	-rm -rf $(BUILDDIR) $(INSTALLDIRS)
	-(cd spidermonkey/src && $(MAKE) clean)

install: $(SOFILE) javascriptlint/jsl javascriptlint/jsl | $(INSTALLDIRS)
	cp $(SOFILE) build/install
	cp javascriptlint/*.py build/install/javascriptlint
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsl >build/install/jsl
	chmod +x build/install/jsl
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsl.py >build/install/javascriptlint/jsl.py
	chmod +x build/install/javascriptlint/jsl.py
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsparse.py >build/install/javascriptlint/jsparse.py
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/lint.py >build/install/javascriptlint/lint.py
	

.PHONY: install
