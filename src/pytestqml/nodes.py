from pathlib import Path

from _pytest.mark import Mark, MarkDecorator
from pytestqml.exceptions import PytestQmlError
from pytestqml.qmlbot import QmlBot

import pytest
from pytestqml.qt import (
    QGuiApplication,
    QtCore,
    QQuickView,
    QPoint,
    Qt,
    Signal,
    QTest,
)
from pytestqml.reporting import (
    get_error_line_in_stack,
    pick_error_context,
    format_stack_trace,
)


class TestView(QQuickView):

    isExposedEvent = Signal()

    def __init__(self, source, ctx_prop, *args):
        self.app = QGuiApplication.instance() or QGuiApplication([])

        super().__init__(*args)
        self.ctx_prop = ctx_prop
        self.qmlbot = QmlBot(self, settings={"whenTimeout": 2000})
        self.isExposedEvent.connect(self.qmlbot.windowShownChanged)

        engine = self.engine()
        engine.clearComponentCache()
        # qmlRegisterType(MyObj, "MyType", 1, 0, "MyObj")
        # print(engine)
        engine.setImportPathList([str(Path(__file__).parent)] + engine.importPathList())
        self.rootContext().setContextProperty("qmlbot", self.qmlbot)

        self._set_context_properties()

        # same as QtTest, don't no if it's needed
        self.setFlags(
            Qt.Window
            | Qt.WindowSystemMenuHint
            | Qt.WindowTitleHint
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
        )

        self.setSource(source)

    def exposeEvent(self, ev):
        super().exposeEvent(ev)
        self.isExposedEvent.emit()

    def setSource(self, source):
        super().setSource(source)

        # Fail if there is some error in source
        if self.status() != QQuickView.Ready:
            pytest.fail("\n".join((err.toString() for err in self.errors())))

        # Avoid hangs with empty windows. don't know if needed, its in QtTest
        self.setFramePosition(QPoint(50, 50))
        if self.size().isEmpty():
            self.resize(200, 200)

    def _set_context_properties(self):
        for k, v in self.ctx_prop.items():
            self.rootContext().setContextProperty(k, v)

    # def keyPressEvent(self, e):
    #     breakpoint()


class QMLFile(pytest.File):
    def __init__(self, fspath, parent):
        super().__init__(fspath, parent)
        self.source = QtCore.QUrl.fromLocalFile(fspath.strpath)

    def collect(self):
        if self.config.getoption("skip-qml"):
            return []
        cp = self.parent.config.hook.pytest_qml_context_properties() or [{}]
        self.view = TestView(
            self.source, cp[0]
        )  # app should exists has long has collect()

        # iter over all children of tst_file.qml root.
        # TestCases are selected if they a name starting with "Test"
        for testcase in self.view.rootObject().children():
            testCaseName = testcase.property("name")

            # each TestCase has to have a `name` property starting with `Test`
            if testCaseName and testCaseName.startswith("Test"):
                testcase.name = testCaseName
                collected_js = testcase.property("collected")
                if collected_js:
                    collected = collected_js.toVariant()
                    for testname in collected:
                        yield QMLItem.from_parent(
                            self, name=testname, testcase=testcase
                        )


class QMLItem(pytest.Item):
    def __init__(self, name, parent, testcase):
        super().__init__(testcase.name + "::" + name, parent)
        self.testname = name
        self.testcase = testcase
        self.add_marker("qmltest")

    def runtest(self):
        view = self.parent.view  # type: TestView
        # relase all buttons, between tests
        QTest.mouseRelease(view, Qt.AllButtons, Qt.NoModifier, QPoint(-1, -1), -1)
        view.setTitle(self.name)

        # execute the test_function
        with view.qmlbot.wait_signal(
            self.testcase.testCompleted,
            timeout=10000,
            raising=True,
        ):
            view.show()
            self.testcase.setProperty("testToRun", self.testname)

        # Process result
        view.close()
        res = self.testcase.property("result").toVariant()
        self._handle_result(res)

    def repr_failure(self, excinfo):
        return excinfo.value

    def reportinfo(self):
        return self.fspath, None, f"{self.parent.name}: {self.name}"

    def _handle_result(self, result: dict):
        if not result:
            return
        elif "type" in result:
            if result["type"] == "SkipError":
                pytest.skip(msg='result["message"]')
            elif result["expectFail"] is not None:
                expfail = result["expectFail"]  # True means xfail and False xpassed
                aa = pytest.mark.xfail(
                    self, reason=result["expectFailMessage"], strict=expfail
                )
                self.add_marker(aa)
                if not expfail:
                    return

        err_msg = self._format_report(result)
        raise PytestQmlError(err_msg)

    def _format_report(self, result: dict):
        report = []
        n = [""]
        filename = self.parent.source.fileName()
        source = self.parent.source.toLocalFile()
        line = get_error_line_in_stack(filename, result["stack"])
        context = pick_error_context(
            source, self.testname, line, result["type"], result["message"].strip("\n")
        )
        # intro = f"""{result["type"]} at line {line}"""
        stack = format_stack_trace(result["stack"], self.testname)
        report = n + context + n + stack
        return "\n".join(report)