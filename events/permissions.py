from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class GestionnaireRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.est_gestionnaire