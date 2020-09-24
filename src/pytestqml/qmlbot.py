from typing import Any, Optional

from pytestqml.qt import (
    QObject,
    Slot,
    QJSValue,
    Signal,
    Property,
    Qt,
    QPoint,
    QTest,
    QKeySequence,
)
from pytestqt.qtbot import QtBot


class QmlBot(QObject):
    """
    Backend used in TestCase for various things.
    view: QQuickView
    settings: dict

    """

    def __init__(self, view: "TestView", settings={}):
        super().__init__()
        self.view = view
        self._settings = settings
        self.expectedToFail = {}
        # self.pressed_keys = set()

    def wait_signal(
        self,
        signal=None,
        timeout=1000,
        raising=None,
        check_params_cb=None,
    ):
        self._should_raise = lambda x: x  # qtbot hack
        return QtBot.wait_signal(
            self,
            signal=signal,
            timeout=timeout,
            raising=raising,
            check_params_cb=check_params_cb,
        )

    """
    Slots are used in PyTest. they should not be called directly but via a method of PyTest.qml
    
    """

    @Slot("QVariant")
    def debug(self, value: Any):
        if isinstance(value, QJSValue):
            value = value.toVariant()
        print(value)

    @Slot(str, str)
    def addExpectToFail(self, tag: str, message: str):
        """
        tag: str =  test_name+tag
        message: str = message
        """
        self.expectedToFail[tag] = message

    @Slot(str, result=bool)
    def isExpectedToFail(self, tag: str):
        return tag in self.expectedToFail

    @Slot(str, result=str)
    def getExpectedToFailMessage(self, tag: str):
        return self.expectedToFail.pop(tag)

    @Slot(QObject, str, result=QObject)
    def findChild(self, parent: QObject, objectName: str) -> Optional[QObject]:
        if not parent:
            return
        return parent.findChild(QObject, objectName)

    @Slot(str, QPoint, int, int, int)
    def mouseEvent(
        self, action: str, point: QPoint, button: int, modifiers: int, delay: int
    ):
        if action == "mouseMove":
            QTest.mouseMove(self.view, point, delay)
        else:
            # Conversion needed for pyqt5/pyside2 compat
            modifiers = Qt.KeyboardModifier(modifiers)
            button = Qt.MouseButton(button)
            getattr(QTest, action)(self.view, button, modifiers, point, delay)

    @Slot(str, int, int, int)
    def keyEvent(
        self,
        action: str,
        key: int,
        modifiers: int = None,
        delay: int = None,
    ):
        # Conversion needed for pyqt5/pyside2 compat
        # print(modifiers)
        key = Qt.Key(key)
        modifiers = Qt.KeyboardModifiers(modifiers)
        getattr(QTest, action)(self.view, key, modifiers, delay)

    @Slot(str)
    def keySequence(self, seq: str):
        QTest.keySequence(self.view, QKeySequence(seq))

    windowShownChanged = Signal()

    @Property(bool, notify=windowShownChanged)
    def windowShown(self) -> bool:
        return self.view.isExposed()

    @Slot(int)
    def wait(self, ms: int) -> None:
        """
        Non UI Blocking wait
        """
        QtBot.wait(self, ms)

    @Slot(str, result=int)
    def settings(self, key: str, value: Any = None):
        return self._settings[key]

    @Slot(str, "QVariant")
    def setSettings(self, key: str, value: Any):
        if isinstance(value, QJSValue):
            value = value.toVariant()
        self._settings[key] = value

    """
    Private api
    """

    # def _event_handler(self):
    #     window = self.engine.rootObjects()[0]
    #     QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(20, 10), 0)
    # def _track_key(self, key):
