import logging
import logging
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    """
    A custom logging handler that emits a PyQt signal for each log record.
    This allows capturing log messages from any module and displaying them
    in a PyQt widget.
    """
    new_record = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        # QObject.__init__ is needed for signals
        QObject.__init__(self)

    def emit(self, record):
        """
        Emits a signal containing the entire log record object.
        """
        self.new_record.emit(record)

def setup_logging(level=logging.INFO):
    """
    Configures the root logger to use the QtLogHandler.
    All log messages from the application will be directed to this handler.
    
    Returns:
        An instance of QtLogHandler which can be connected to a slot.
    """
    # Create the handler instance
    qt_handler = QtLogHandler()

    # Configure the root logger. 
    # force=True is important to allow reconfiguration if logging was already set up.
    logging.basicConfig(level=level,
                        handlers=[qt_handler],
                        force=True)

    logging.getLogger('PyQt6').setLevel(logging.WARNING)

    return qt_handler
