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
	PY_PREFIX=$(shell python2.6 -c "import sys; sys.stdout.write(sys.prefix)")
	PY_FIRST_ARCH=$(shell set -x; file `which python2.6` | grep "for architecture" | head -1 | awk '{print $$NF}')
	CPPFLAGS += -I$(PY_PREFIX)/include/python2.6
	SOLDFLAGS += $(PY_PREFIX)/Python
	LD=gcc -arch $(PY_FIRST_ARCH)
	CC=gcc -arch $(PY_FIRST_ARCH)
else
# This is known to work on 2.6 and 2.7.
	PY_PREFIX=$(shell python -c "import sys; sys.stdout.write(sys.prefix)")
	PY_VERSION=$(shell python -c "import sys; import platform; sys.stdout.write(platform.python_version()[0:3])")
	CPPFLAGS += \
		-I$(PY_PREFIX)/include/python$(PY_VERSION)
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
	cp javascriptlint/jsl $(SOFILE) build/install
	cp javascriptlint/*.py build/install/javascriptlint

.PHONY: install
