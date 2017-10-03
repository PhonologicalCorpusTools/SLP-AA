from imports import *
from collections import defaultdict
import parameters
import anytree

class ParameterTreeWidget(QTreeWidget):
    itemChecked = Signal(object, int)

    def __init__(self, parent, model, checkStrategy='defaults'):
        super().__init__()
        self.parent = parent
        self.model = model
        self.buttonGroups = defaultdict(list)
        self.specialButtons = list()
        self.itemClicked.connect(self.handleItemChanged)
        self.currentItemChanged.connect(self.handleItemChanged)
        self.currentItemChanged.connect(self.parent.updateDisplayTree)

        for parameter in self.model.tree.children:
            displayNode = anytree.Node(parameter.name, parent=self.parent.displayTree)
            parentWidgetItem = ParameterTreeWidgetItem(self, parameter=parameter)
            parentWidgetItem.setFlags(Qt.ItemIsSelectable | parentWidgetItem.flags() ^ Qt.ItemIsUserCheckable)
            parentWidgetItem.setText(0, parameter.name)
            self.addChildren(parentWidgetItem, parameter, displayNode, checkStrategy=checkStrategy)

        self.buttonGroups['Major Location'].extend(self.specialButtons)

    def addChildren(self, parentWidgetItem, parentParameter, displayNode, checkStrategy='defaults'):
        buttonGroup = list()
        appendGroup = False

        for c in parentParameter.children:
            child = ParameterTreeWidgetItem(parentWidgetItem, parameter=c)
            if c.is_leaf:
                child.setText(0, c.name)
                child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                if checkStrategy == 'defaults' and c.parameter.is_default:
                    child.setCheckState(0, Qt.Checked)
                    c.is_checked = True
                elif checkStrategy == 'load' and c.is_checked:
                    child.setCheckState(0, Qt.Checked)
                else:
                    child.setCheckState(0, Qt.Unchecked)
                    c.is_checked = False
                buttonGroup.append(child)
                appendGroup = True

            else:
                #it's a non-terminal node
                newDisplayNode = anytree.Node(c.name, parent=displayNode)
                child.setText(0, c.name)
                if parentParameter.name == 'Major Location':
                    child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    child.setCheckState(0, Qt.Unchecked)
                    if c.name == 'Body location':
                        child.setCheckState(0, Qt.Checked)
                        c.is_checked = True
                    self.specialButtons.append(child)
                else:
                    child.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable^child.flags())
                self.addChildren(child, c, newDisplayNode, checkStrategy=checkStrategy)
        if appendGroup:
            self.buttonGroups[parentParameter.name].extend(buttonGroup)

    def resetModel(self, model):
        self.model = model

    def resetChecks(self):
        treeItem = self.invisibleRootItem()
        self._resetChecks(treeItem, checkStrategy='defaults')

    def clearChecks(self):
        treeItem = self.invisibleRootItem()
        self._resetChecks(treeItem, checkStrategy='clear')

    def loadChecks(self):
        treeItem = self.invisibleRootItem()
        self._resetChecks(treeItem, checkStrategy='load')

    def _resetChecks(self, treeItem, checkStrategy):
        for n in range(treeItem.childCount()):
            child = treeItem.child(n)
            if child.flags() & Qt.ItemIsUserCheckable:
                if checkStrategy == 'clear':
                    child.setCheckState(0, Qt.Unchecked)
                    child.is_checked = False
                elif checkStrategy == 'load':
                    if child.parameter.is_checked:
                        child.setCheckState(0, Qt.Checked)
                    else:
                        child.setCheckState(0, Qt.Unchecked)
                elif checkStrategy == 'defaults':
                    if child.parameter.is_default:
                        child.setCheckState(0, Qt.Checked)
                        child.is_checked = True
                    else:
                        child.setCheckState(0, Qt.Unchecked)
                        child.is_checked = False
            if child.childCount() > 0:
                self._resetChecks(child, checkStrategy=checkStrategy)

    def getChildren(self, node):
        if not node.childCount():
            yield node
        else:
            for n in range(node.childCount()):
                child = node.child(n)
                yield child
                self.getChildren(child)

    def topDownIter(self):
        topNode = self.invisibleRootItem()
        for node in range(topNode.childCount()):
            child = topNode.child(node)
            self.getChildren(child)

    def handleItemChanged(self, item, column):
        if item is None or item.parent() is None:
            return
        addToTree = False
        parentName = item.parent().text(0)
        treeResolver = anytree.Resolver('name')
        path = self.makeTreePath(item)
        parameterNode = treeResolver.get(self.model.tree, path)
        for childNode in parameterNode.children:
            if childNode.name == item.text(0):
                childNode.is_checked = True
            else:
                childNode.is_checked = False

        for button in self.buttonGroups[parentName]:
            if button.text(0) == item.text(0):
                button.setCheckState(0, Qt.Checked)
                addToTree = True
            else:
                button.setCheckState(0, Qt.Unchecked)
        self.parent.updateDisplayTree(addToTree)

    def findTopParent(self, item):
        parent = item.parent()
        while True:
            if parent.parent() is None:
                break
            else:
                parent = parent.parent()
        return parent

    def makeTreePath(self, item):
        path = list()
        parent = item.parent()
        path.append(parent.text(0))
        while True:
            if parent.parent() is None:
                break
            else:
                parent = parent.parent()
                path.append(parent.text(0))
        path.reverse()
        path = '/'.join(path)
        return path

class ParameterSelectionsLayout(QHBoxLayout):

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.values = list()
        self.addWidget(QLabel(self.name))

    def addLabel(self, text):
        setattr(self, text+'Label', QLabel(text))
        self.values.append(text+'Label')
        self.addWidget(getattr(self, text+'Label'))

    def changeText(self, labelName, newText):
        widgetName = labelName+'Label'
        for value in self.values:
            if value == widgetName:
                getattr(self, widgetName).setText(' : '.join([labelName, newText]))
                break

class ParameterDialog(QDialog):

    def __init__(self, model, checkStrategy='defaults'):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle('Select Parameters')
        self.adjustedHeight = self.frameGeometry().height()
        self.adjustedWidth = self.frameGeometry().width()
        self.adjustedPos = self.pos()
        self.model = model
        self.displayTree = anytree.Node('Selected Parameters', parent=None)
        self.selectionLayout = QVBoxLayout()
        self.displayTreeWidget = QTextEdit()
        self.treeWidget = ParameterTreeWidget(self, self.model, checkStrategy=checkStrategy)

        layout = QVBoxLayout()
        self.parameterLayout = QHBoxLayout()

        self.generateDisplayTreeText()
        self.selectionLayout.addWidget(self.displayTreeWidget)
        self.parameterLayout.addWidget(self.treeWidget)
        self.parameterLayout.addLayout(self.selectionLayout)

        terminalNodesLayout = QVBoxLayout()
        self.terminalNodesLabel = QTextEdit('No parameters selected')
        terminalNodesLayout.addWidget(self.terminalNodesLabel)
        self.parameterLayout.addLayout(terminalNodesLayout)

        buttonLayout = QGridLayout()
        okButton = QPushButton('OK')
        cancelButton = QPushButton('Cancel')
        resetButton = QPushButton('Reset to default values')
        clearButton = QPushButton('Clear all check boxes')
        buttonLayout.addWidget(resetButton,0, 0)
        buttonLayout.addWidget(clearButton,0, 1)
        buttonLayout.addWidget(okButton, 1, 0)
        buttonLayout.addWidget(cancelButton, 1, 1)
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        resetButton.clicked.connect(self.reset)
        clearButton.clicked.connect(self.clear)

        layout.addLayout(self.parameterLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.resize(self.adjustedHeight, self.adjustedWidth)
        self.move(self.adjustedPos)

    def resetTreeWidget(self, model):
        self.parameterLayout.removeWidget(self.treeWidget)
        self.treeWidget = ParameterTreeWidget(self, model)
        self.parameterLayout.addWidget(self.treeWidget)

    def getSignParameters(self):
        r = anytree.Resolver('name')
        quality = r.get(self.treeWidget.model.tree, 'Quality')
        for child in quality.children:
            print(child.name)
            for terminal in child.children:
                print(terminal.name, terminal.is_checked)
        return self.treeWidget.model.getParameters()

    def reset(self):
        continue_ = self.showWarning()
        if continue_:
            self.treeWidget.resetChecks()
            self.updateDisplayTree(True)

    def clear(self):
        continue_ = self.showWarning()
        if continue_:
            self.treeWidget.clearChecks()
            self.updateDisplayTree(True)

    def showWarning(self):
        alert = QMessageBox()
        alert.setWindowFlags(Qt.WindowStaysOnTopHint)
        alert.setWindowTitle('Warning')
        alert.setText('This will erase your currently selected parameters. This action cannot be undone. Continue?')
        alert.addButton('OK', QMessageBox.AcceptRole)
        alert.addButton('Cancel', QMessageBox.RejectRole)
        alert.exec_()
        role = alert.buttonRole(alert.clickedButton())
        if role == QMessageBox.AcceptRole:
            return True
        else:
            return False

    def closeEvent(self, e):
        self.close()

    def accept(self):
        self.adjustedHeight = self.frameGeometry().height()
        self.adjustedWidth = self.frameGeometry().width()
        self.adjustedPos = self.pos()
        self.hide()

    def reject(self):
        self.adjustedHeight = self.frameGeometry().height()
        self.adjustedWidth = self.frameGeometry().width()
        self.adjustedPos = self.pos()
        self.hide()

    def generateDisplayTreeText(self):
        treeText = list()
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            treeText.append("{}{}".format(pre, node.name))
        treeText = '\n'.join(treeText)
        self.displayTreeWidget.setText(treeText)

    def buildTree(self, treeWidgetItem, displayTreeItem):
        canBeChecked = treeWidgetItem.flags() & Qt.ItemIsUserCheckable
        if (not canBeChecked) or (canBeChecked and treeWidgetItem.checkState(0)):
            newDisplayNode = anytree.Node(treeWidgetItem.text(0), parent=displayTreeItem)
            for n in range(treeWidgetItem.childCount()):
                child = treeWidgetItem.child(n)
                self.buildTree(child, newDisplayNode)

    def updateDisplayTree(self, addToTree=None):
        if not addToTree:
            return

        topNode = anytree.Node('Selected Parameters', parent=None)
        root = self.treeWidget.invisibleRootItem()
        self.buildTree(root, topNode)
        self.displayTree = topNode

        treeText = list()
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            treeText.append("{}{}".format(pre, node.name))
        self.displayTreeWidget.clear()
        self.displayTreeWidget.setText('\n'.join(treeText))
        self.updateTerminalNodes()

    def updateTerminalNodes(self):
        text = list()
        true_children = [node.name for pre, fill, node in anytree.RenderTree(self.model.tree) if node.is_leaf]
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            if node.is_leaf and node.name in true_children:
                text.append(' : '.join([node.parent.name, node.name]))
        text = '\n'.join(text)
        self.terminalNodesLabel.setText(text)

class ParameterTreeWidgetItem(QTreeWidgetItem):

    def __init__(self, parent, parameter=None):
        super().__init__(parent)
        self.parameter = parameter

    def setData(self, column, role, value):
        state = self.checkState(column)
        super().setData(column, role, value)
        if (role == Qt.CheckStateRole and
            state != self.checkState(column)):
            treewidget = self.treeWidget()
            if treewidget is not None:
                treewidget.itemChecked.emit(self, column)

class ParameterTreeModel:

    def __init__(self, parameterList, startNode = None):
        self.tree = anytree.Node('Parameters', parent=None)
        self.parameterList = parameterList
        for p in parameterList:
            parameterNode = ParameterNode(p, parent=self.tree) #anytree.Node(p.name, parent=self.tree)
            setattr(self, p.name, parameterNode)
            for child in p.children:
                self.addNode(child, parameterNode)

    def exportTree(self):
        export = list()
        # r = anytree.Resolver('name')
        # top = r.get(self.tree, '/Parameters')
        for pre, fill, node in anytree.RenderTree(self.tree):
            if node.is_leaf:
                if node.is_checked:
                    export.append("{}:{}".format(node.parent.name, node.name))
        export = ','.join(export)
        return export

    def __str__(self):
        return self.exportTree()

    def printTree(self, nodeName='Quality'):
        treeText = list()
        r = anytree.Resolver('name')
        quality = r.get(self.tree, nodeName)
        for pre, fill, node in anytree.RenderTree(quality):
            if node.is_leaf:
                if node.is_checked:
                    treeText.append("{}{}".format(pre, node.name))
            else:
                treeText.append("{}{}".format(pre, node.name))

        treeText = '\n'.join(treeText)
        print(treeText)


    def getTree(self):
        return self.tree

    def getParameters(self):
        return self.parameterList

    def addNode(self, parameter, parentNode):
        if parameter.children:
            newNode = ParameterNode(parameter, parent=parentNode)#anytree.Node(parameter.name, parent=parentNode)
            for c in parameter.children:
                self.addNode(c, newNode)
        else:
            newNode = ParameterNode(parameters.TerminalParameter(parameter.name, parentNode), parent=parentNode) #anytree.Node(parameter, parent=parentNode)

    def __getitem__(self, item):
        for node in self.tree.children:
            if node.name == item:
                return node
        else:
            return None

    def __iter__(self):
        for node in self.tree.children:
            yield node.name


class ParameterNode(anytree.Node):

    def __init__(self, parameter, parent=None, checked=None):
        super().__init__(parameter.name, parent=parent)
        self.name = parameter.name
        self.parameter = parameter
        self.is_default = self.parameter.is_default
        if checked is None:
            self.is_checked = self.is_default
        else:
            self.is_checked = checked
        if isinstance(self.parameter, parameters.TerminalParameter):
           self.default = None
        else:
            self.default = self.parameter.default

    def printTree(self):
        treeText = list()
        for pre, fill, node in anytree.RenderTree(self):
            treeText.append("{}{}".format(pre, node.name))
        treeText = '\n'.join(treeText)
        print(treeText)