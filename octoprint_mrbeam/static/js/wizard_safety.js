$(function() {
    function WizardSafetyViewModel(parameters) {
        var self = this;

        self.loginStateViewModel = parameters[0];


        self.checkbox1 = ko.observable(false);
        self.checkbox2 = ko.observable(false);
        self.checkbox3 = ko.observable(false);
        self.checkbox4 = ko.observable(false);
        self.checkbox5 = ko.observable(false);
        self.checkbox6 = ko.observable(false);

        self.showAgain = ko.observable(true);


        self.allChecked = ko.pureComputed(function() {
            return (self.checkbox1() &&
                self.checkbox2() &&
                self.checkbox3() &&
                self.checkbox4() &&
                self.checkbox5() &&
                self.checkbox6());
        });

        self.onBeforeWizardTabChange = function(next, current) {
            if (current && _.startsWith(current, "wizard_plugin_corewizard_safety")) {
                if (self.allChecked()) {
                    var data = {
                        "username": self.loginStateViewModel.username(),
                        "ts": Date.now().toString(),
                        "showAgain": self.showAgain()
                    };
                    self._sendData(data);
                    return true;
                } else {
                    showMessageDialog({
                        title: gettext("You need to agree to all points"),
                        message: gettext("Please read the entire document and indicate that you understood and agree by checking all checkboxes.")
                    });
                    return false;
                }
            }
            return true;
        };

        self._sendData = function(data) {
            OctoPrint.simpleApiCommand("mrbeam", "safety_wizard_confirmation", data);
        };

    }

    OCTOPRINT_VIEWMODELS.push([
        WizardSafetyViewModel,
        ["loginStateViewModel"],
        "#wizard_plugin_corewizard_safety"
    ]);
});