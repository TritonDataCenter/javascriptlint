BUILDOS=$(shell uname -s)
BUILDDIR = build
INSTALLDIRS =					\
	$(BUILDDIR)/install			\
	$(BUILDDIR)/install/javascriptlint	\

PY_PYTHON=$(shell python2.7 -c "import sys; print(sys.executable)")
PY_PREFIX=$(shell $(PY_PYTHON) -c "import sys; print(sys.real_prefix)" || $(PY_PYTHON) -c "import sys; print(sys.prefix)")
PY_VERSION=$(shell $(PY_PYTHON) -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

CPPFLAGS += -I$(PY_PREFIX)/include/python$(PY_VERSION)

$(BUILDDIR) $(INSTALLDIRS):
	mkdir -p $@

clean:
	-rm -rf $(BUILDDIR) $(INSTALLDIRS)

install: javascriptlint/jsl javascriptlint/jsl | $(INSTALLDIRS)
	cp -r jsengine build/install
	cp javascriptlint/*.py build/install/javascriptlint
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsl >build/install/jsl
	chmod +x build/install/jsl
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsl.py >build/install/javascriptlint/jsl.py
	chmod +x build/install/javascriptlint/jsl.py
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/jsparse.py >build/install/javascriptlint/jsparse.py
	sed -e "1s:#\!/usr/bin/env python:#\!$(PY_PYTHON):" javascriptlint/lint.py >build/install/javascriptlint/lint.py

.PHONY: install
