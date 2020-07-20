# -*- coding: utf-8 -*-
"""
/***************************************************************************
 criar_pontos_rios
                                 A QGIS plugin
 Cria pontos de inicio, fim e confluentes dos Rios.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-07-15
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Antônio Teles
        email                : antoniot.leandro@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.PyQt import QtCore
from qgis.gui import *
from PyQt5 import QtCore, QtGui
import pdb
from qgis.core import QgsProject, QgsFeature,QgsFields,QgsVectorFileWriter, QgsField, QgsGeometry, QgsPoint, QgsMapLayer, QgsVectorLayer, QgsWkbTypes, QgsVectorLayerUtils

from qgis.gui import QgsMessageBar, QgsMapCanvas, QgsMapCanvasItem
import qgis.utils
import os
from collections import defaultdict

from shapely.wkb import loads
from osgeo import ogr

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog



# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .CriarPontosRios_dialog import criar_pontos_riosDialog
import os.path


class criar_pontos_rios:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'criar_pontos_rios_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.dlg = criar_pontos_riosDialog()
        self.actions = []
        self.menu = self.tr(u'&Criar Pontos nos Rios')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.toolbar = self.iface.addToolBar(u'CriarPontosRios')
        self.toolbar.setObjectName(u'CriarPontosRios')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('criar_pontos_rios', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/CriarPontosRios/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Criar Pontos Rios (I.F.C)'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

        self.dlg.caminho.clear()
        self.dlg.select_caminho.clicked.connect(self.selecione_caminho)


        


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Criar Pontos nos Rios'),
                action)
            self.iface.removeToolBarIcon(action)

    def set_select_attributes(self):
        self.dlg.coluna.clear()
        if self.dlg.select_layer.currentText() != "":
            layername = self.dlg.select_layer.currentText()
            for selectlayers in QgsProject.instance().mapLayers().values():
                if selectlayers.name() == layername:
                    for field in selectlayers.dataProvider().fields():
                        self.dlg.coluna.addItem(field.name())
    
    def selecione_caminho(self):
        # Abri janela para escolher caminho onde vai salvar o shape
        filtering="Shapefiles (*.shp *.SHP)"
        settings = QSettings()
        dirName = settings.value("/UI/lastShapefileDir")
        encode = settings.value("/UI/encoding")
        fileDialog = QgsEncodingFileDialog(None, QCoreApplication.translate("fTools", "Save output shapefile"), dirName, filtering, encode)
        fileDialog.setDefaultSuffix("shp")
        fileDialog.setFileMode(QFileDialog.AnyFile)
        fileDialog.setAcceptMode(QFileDialog.AcceptSave)
        #fileDialog.setConfirmOverwrite(True)
        if not fileDialog.exec_() == QDialog.Accepted:
            return None, None

        files = fileDialog.selectedFiles()
        settings.setValue("/UI/lastShapefileDir", QFileInfo(unicode(files[0])).absolutePath())
        self.outFilePath = unicode(files[0])
        self.encoding = unicode(fileDialog.encoding())
        self.dlg.caminho.setText(self.outFilePath)
        self.nomeshape = files

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        
        #Limpa o caminho pra salvar o arquivo
        self.dlg.caminho.clear() 

        # Carrega os Layer que corresponde somente a Shp de polylines
        layers = QgsProject.instance().mapLayers().values()
        self.dlg.select_layer.clear()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry:
                self.dlg.select_layer.addItem( layer.name(), layer )  
        self.set_select_attributes()

        # Carrega as colunas dos shape sempre que seleciona os shape
        self.dlg.select_layer.currentIndexChanged.connect(self.set_select_attributes)
        self.set_select_attributes()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.

            listcom = []
            
            # Seleciona Somente o Shape que foi escolhido
            for selectlayer in QgsProject.instance().mapLayers().values():
                if selectlayer.name() == self.dlg.select_layer.currentText():
                    coluna = self.dlg.coluna.currentText()
                    lay = selectlayer
                    sRs = lay.crs()
                    provider = lay.dataProvider()
                    n_new_feats = 0
                    for i in lay.getFeatures():
                        geomVerif = i.geometry()
                        print(i.geometry())
                        print(i.attributes())
                        geomSingleType = QgsWkbTypes.isSingleType(geomVerif.wkbType())
                        if not geomSingleType:
                            geomFeature = geomVerif.asGeometryCollection()
                    
                    if not geomSingleType:
                        
                        a_list = []
                        vlayer = QgsVectorLayer("LineString?", "vlayer", "memory" )
                        pr = vlayer.dataProvider()
                        for feature in lay.getFeatures():
                            geomMult = feature.geometry()
                            a_list.append(feature[coluna])

                            if geomMult.isMultipart():                             
                                geom_list = geomMult.asMultiPolyline()

                                listTeste = []
                                for single_geom_list in geom_list:
                                    corrdsList = []
                                    for coords in single_geom_list: 
                                        corrdsList.append(QgsPoint(coords)) 
                                    single_feature = QgsFeature()
                                    single_geom = QgsGeometry.fromPolyline(corrdsList)

                                    single_feature.setGeometry(single_geom)
                                    pr.addFeature(single_feature)
                        vlayer.updateExtents()
                    if geomSingleType:
                        for f in lay.getFeatures():
                            nome = f[coluna]
                            geom = f.geometry()
                            wkb = geom.asWkb()
                            geom_ogr = ogr.CreateGeometryFromWkb(wkb)
                            vertices = geom.asPolyline()
                

                            n = len(vertices) - 1

                            xi = geom_ogr.GetX(0)
                            yi = geom_ogr.GetY(0)
                            zi = geom_ogr.GetZ(0)

                            xf = geom_ogr.GetX(n)
                            yf = geom_ogr.GetY(n)
                            zf = geom_ogr.GetZ(n)
                                
                            if geom_ogr.GetZ(0) == geom_ogr.GetZ(n):
                                list = [xi,yi,zi,nome,'Inicio']
                                listcom.append(list)
                                list2 = [xf,yf,zf,nome,'Fim']
                                listcom.append(list2)

                            elif geom_ogr.GetZ(0) < geom_ogr.GetZ(n): 
                                list3 = [xi,yi,zi,nome,'Fim']
                                listcom.append(list3)
                                list4 = [xf,yf,zf,nome,'Inicio']
                                listcom.append(list4)

                            elif geom_ogr.GetZ(0) > geom_ogr.GetZ(n):
                                list5 = [xi,yi,zi,nome,'Inicio']
                                listcom.append(list5)
                                list6 = [xf,yf,zf,nome,'Fim']
                                listcom.append(list6)
                    else :
                        for f in vlayer.getFeatures():
                            nome = a_list[n_new_feats]
                            geom = f.geometry()
                            wkb = geom.asWkb()
                            geom_ogr = ogr.CreateGeometryFromWkb(wkb)
                            vertices = geom.asPolyline()
                

                            n = len(vertices) - 1

                            xi = geom_ogr.GetX(0)
                            yi = geom_ogr.GetY(0)
                            zi = geom_ogr.GetZ(0)

                            xf = geom_ogr.GetX(n)
                            yf = geom_ogr.GetY(n)
                            zf = geom_ogr.GetZ(n)
                                
                            if geom_ogr.GetZ(0) == geom_ogr.GetZ(n):
                                list = [xi,yi,zi,nome,'Inicio']
                                listcom.append(list)
                                list2 = [xf,yf,zf,nome,'Fim']
                                listcom.append(list2)

                            elif geom_ogr.GetZ(0) < geom_ogr.GetZ(n): 
                                list3 = [xi,yi,zi,nome,'Fim']
                                listcom.append(list3)
                                list4 = [xf,yf,zf,nome,'Inicio']
                                listcom.append(list4)

                            elif geom_ogr.GetZ(0) > geom_ogr.GetZ(n):
                                list5 = [xi,yi,zi,nome,'Inicio']
                                listcom.append(list5)
                                list6 = [xf,yf,zf,nome,'Fim']
                                listcom.append(list6)
                            n_new_feats += 1
            listfinal = []
            listverif = []
            
            v = 0


            for s in listcom:
                valorXY = [listcom[v][0],listcom[v][1]]
                listverif.append(valorXY)
                v += 1
            
            for d in listverif:
                rX1 = d[0]
                rY1 = d[1]
                resultado = 0
                for resp in listverif:
                    rX2 = resp[0]
                    rY2 = resp[1]
                    if rX1 == rX2 and rY1 == rY2:
                        resultado += 1

                tfinal = 0
                for j in listfinal:
                    if j[0] == d[0] and j[1] == d[1]:
                        tfinal = 1
                if tfinal == 0 :
                    if resultado == 1:
                        for verifin in listcom:
                            if verifin[0] == d[0] and verifin[1] == d[1]:
                                listfinal.append(verifin)
                    else :
                    
                        v2 = 0
                        Listrio = []
                        
                        for verif in listcom:
                            if verif[0] == d[0] and verif[1] == d[1]:
                                altitude = verif[2]
                                nome_rio = verif[3]
                                Listrio.append(nome_rio)
                                riofinal = verif[3]

                        riot = 0
                        for rio in Listrio:
                            riot = 0
                            for riofin in Listrio:
                                if rio == riofin :
                                    riot += 1
                            if riot == 2:
                                if rio != '' or rio != None:
                                    riofinal = rio
                        valorfinal = [d[0],d[1],altitude,riofinal,'Confluencia']                        
                        del Listrio
                        listfinal.append(valorfinal)


            self.Fields = QgsFields()
            self.Fields.append(QgsField('id',QVariant.Int))
            self.Fields.append(QgsField('nome',QVariant.String))
            self.Fields.append(QgsField('situacao',QVariant.String))

            global SHPCaminho
            SHPCaminho = self.outFilePath
            self.outputPointsShape = QgsVectorFileWriter(SHPCaminho, self.encoding, self.Fields, QgsWkbTypes.Point, sRs, "ESRI Shapefile")
            idX = 1
            for final in listfinal:
                self.fetf = QgsFeature()
                zPoint = QgsPoint(final[0], final[1], final[2])
                zPoint.z()
                self.fetf.setGeometry( QgsGeometry( zPoint ) )
                self.fetf.setAttributes([idX, final[3], final[4]] )
                self.outputPointsShape.addFeature(self.fetf)
                idX += 1
            
            pegarNome = self.outFilePath
            Nomes = pegarNome.split( '/' )
            contNomes = len(Nomes) - 1
            nomefinalshp = Nomes[contNomes]
            nomefinalshp =  nomefinalshp.replace('.shp','')
            nomefinalshp =  nomefinalshp.replace('.SHP','')
            #self.iface.addVectorLayer(self.outFilePath, nomefinalshp, 'ogr')
            self.layer = QgsVectorLayer(self.outFilePath, nomefinalshp, "ogr")
            if not self.layer.isValid():
                raise ValueError("Failed to open the layer")
            self.canvas = QgsMapCanvas()
            QgsProject.instance().addMapLayer(self.layer)
            self.canvas.setExtent(self.layer.extent())
            self.canvas.setLayers([self.layer])
            del self.outputPointsShape
            QgsProject.instance().removeMapLayer(self.layer)
            self.layer = QgsVectorLayer(self.outFilePath, nomefinalshp, "ogr")
            QgsProject.instance().addMapLayer(self.layer)
