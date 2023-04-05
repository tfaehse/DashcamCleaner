# -*- coding: utf-8 -*-
# flake8: noqa
################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.3.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(822, 310)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.line_source = QLineEdit(self.centralwidget)
        self.line_source.setObjectName(u"line_source")
        self.line_source.setEnabled(True)
        self.line_source.setReadOnly(True)

        self.horizontalLayout.addWidget(self.line_source)

        self.button_source = QPushButton(self.centralwidget)
        self.button_source.setObjectName(u"button_source")

        self.horizontalLayout.addWidget(self.button_source)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.line_target = QLineEdit(self.centralwidget)
        self.line_target.setObjectName(u"line_target")
        self.line_target.setEnabled(True)
        self.line_target.setReadOnly(True)

        self.horizontalLayout_2.addWidget(self.line_target)

        self.button_target = QPushButton(self.centralwidget)
        self.button_target.setObjectName(u"button_target")

        self.horizontalLayout_2.addWidget(self.button_target)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.line = QFrame(self.centralwidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.spin_blur = QSpinBox(self.centralwidget)
        self.spin_blur.setObjectName(u"spin_blur")
        self.spin_blur.setValue(9)

        self.horizontalLayout_3.addWidget(self.spin_blur)

        self.label_9 = QLabel(self.centralwidget)
        self.label_9.setObjectName(u"label_9")

        self.horizontalLayout_3.addWidget(self.label_9)

        self.spin_feather_edges = QSpinBox(self.centralwidget)
        self.spin_feather_edges.setObjectName(u"spin_feather_edges")
        self.spin_feather_edges.setValue(1)

        self.horizontalLayout_3.addWidget(self.spin_feather_edges)

        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_3.addWidget(self.label_5)

        self.double_spin_threshold = QDoubleSpinBox(self.centralwidget)
        self.double_spin_threshold.setObjectName(u"double_spin_threshold")
        self.double_spin_threshold.setMaximum(1.000000000000000)
        self.double_spin_threshold.setSingleStep(0.050000000000000)
        self.double_spin_threshold.setValue(0.300000000000000)

        self.horizontalLayout_3.addWidget(self.double_spin_threshold)

        self.label_6 = QLabel(self.centralwidget)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_3.addWidget(self.label_6)

        self.double_spin_roimulti = QDoubleSpinBox(self.centralwidget)
        self.double_spin_roimulti.setObjectName(u"double_spin_roimulti")
        self.double_spin_roimulti.setMinimum(0.800000000000000)
        self.double_spin_roimulti.setMaximum(10.000000000000000)
        self.double_spin_roimulti.setSingleStep(0.050000000000000)
        self.double_spin_roimulti.setValue(1.000000000000000)

        self.horizontalLayout_3.addWidget(self.double_spin_roimulti)

        self.label_10 = QLabel(self.centralwidget)
        self.label_10.setObjectName(u"label_10")

        self.horizontalLayout_3.addWidget(self.label_10)

        self.spin_memory = QSpinBox(self.centralwidget)
        self.spin_memory.setObjectName(u"spin_memory")
        self.spin_memory.setMaximum(10)

        self.horizontalLayout_3.addWidget(self.spin_memory)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.line_2 = QFrame(self.centralwidget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_4.addWidget(self.label)

        self.combo_box_weights = QComboBox(self.centralwidget)
        self.combo_box_weights.setObjectName(u"combo_box_weights")

        self.horizontalLayout_4.addWidget(self.combo_box_weights)

        self.label_8 = QLabel(self.centralwidget)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_4.addWidget(self.label_8)

        self.spin_batch = QSpinBox(self.centralwidget)
        self.spin_batch.setObjectName(u"spin_batch")
        self.spin_batch.setMinimum(1)
        self.spin_batch.setMaximum(256)
        self.spin_batch.setValue(16)

        self.horizontalLayout_4.addWidget(self.spin_batch)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_4.addWidget(self.label_2)

        self.spin_blur_workers = QSpinBox(self.centralwidget)
        self.spin_blur_workers.setObjectName(u"spin_blur_workers")
        self.spin_blur_workers.setMinimum(1)
        self.spin_blur_workers.setMaximum(128)

        self.horizontalLayout_4.addWidget(self.spin_blur_workers)

        self.label_7 = QLabel(self.centralwidget)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_4.addWidget(self.label_7)

        self.spin_quality = QSpinBox(self.centralwidget)
        self.spin_quality.setObjectName(u"spin_quality")
        self.spin_quality.setMaximum(10)
        self.spin_quality.setValue(5)

        self.horizontalLayout_4.addWidget(self.spin_quality)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.line_3 = QFrame(self.centralwidget)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.HLine)
        self.line_3.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.progress = QProgressBar(self.centralwidget)
        self.progress.setObjectName(u"progress")
        self.progress.setEnabled(True)
        self.progress.setValue(0)

        self.horizontalLayout_5.addWidget(self.progress)

        self.button_start = QPushButton(self.centralwidget)
        self.button_start.setObjectName(u"button_start")

        self.horizontalLayout_5.addWidget(self.button_start)

        self.button_abort = QPushButton(self.centralwidget)
        self.button_abort.setObjectName(u"button_abort")
        self.button_abort.setEnabled(False)

        self.horizontalLayout_5.addWidget(self.button_abort)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.line_4 = QFrame(self.centralwidget)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.HLine)
        self.line_4.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line_4)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_7.addWidget(self.label_4)

        self.label_status = QLabel(self.centralwidget)
        self.label_status.setObjectName(u"label_status")

        self.horizontalLayout_7.addWidget(self.label_status)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addLayout(self.horizontalLayout_7)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"DashcamCleaner", None))
        self.button_source.setText(QCoreApplication.translate("MainWindow", u"Select video", None))
        self.button_target.setText(QCoreApplication.translate("MainWindow", u"Select target", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Blur size", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Feather edges", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Detection threshold", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"ROI enlargement", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Blur memory", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Model", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Batch size", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Blur workers", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Output Quality", None))
        self.button_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.button_abort.setText(QCoreApplication.translate("MainWindow", u"Abort", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Status", None))
        self.label_status.setText(QCoreApplication.translate("MainWindow", u"idle", None))
    # retranslateUi

