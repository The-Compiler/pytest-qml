import QtQuick 2.14
import PyTest 1.0
import ".."
import MyNewType 1.0

/*
Ne MODIFIER CE FICHIER QUE PAR LE BAS POUR GARDER LA NUMEROTATION
*/

Item {
    id: item
    Bla {
        id: bla
    }
    TestCase {
        name: "TestRienSans"
        function test_simple(){
            compare(1,1)
        }

        function test_deuxieme(){
            compare(1,1)
        }
        function test_custom_comp(){
            let comp = Qt.createComponent("../Comp.qml")
            let c = createTemporaryObject(comp, item)
            mouseClick(c)
            compare(c.text, "bla")
        }
        function test_custom_type1(){
            compare(bla.rien, "rien")
        }
        function test_custom_type2(){
            compare(bla.rien, "rien")
        }
        function test_custom_type3(){
            compare(bla.rien, "rien")
        }
        function test_contest_property() {
            compare(cp.customSlot(), "customSlot")
        }
    }
}