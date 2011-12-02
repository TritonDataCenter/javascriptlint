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
CPPFLAGS += -DNDEBUG -D_REENTRANT		\
	-Ispidermonkey/src			\
	-Ispidermonkey/src/build		\
	-I/usr/include

SOLDFLAGS += -shared

ifeq ($(BUILDOS),Darwin)
	# Assumes you've done `brew install python` (2.7)
	CC=gcc
	LD=gcc
	CPPFLAGS += -I/usr/local/include/python2.7
	SOLDFLAGS += -L/usr/local/lib -lpython2.7
else
	CPPFLAGS +=					\
	-I/opt/local/include/db4			\
	-I/opt/local/include/ncurses 			\
	-I/opt/local/include/python2.4
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
	(cd spidermonkey/src && $(MAKE))

spidermonkey/src/build/js_operating_system.h:
	echo "#define XP_UNIX" > $@

clean:
	-rm -rf $(BUILDDIR) $(INSTALLDIRS)
	-(cd spidermonkey/src && $(MAKE) clean)

install: $(SOFILE) javascriptlint/jsl javascriptlint/jsl | $(INSTALLDIRS)
	cp javascriptlint/jsl $(SOFILE) build/install
	cp javascriptlint/*.py build/install/javascriptlint

.PHONY: install
