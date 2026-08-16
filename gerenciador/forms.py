from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import VaultGroup, VaultItem


# Cadastro de usuários.
class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["username"].help_text = (
            "Até 150 caracteres; use letras, números e @ . + - _."
        )
        self.fields["password1"].label = "Senha"
        self.fields["password1"].help_text = (
            "Use ao menos 8 caracteres; não repita o usuário nem use senha comum "
            "ou apenas números."
        )
        self.fields["password2"].label = "Confirmar senha"
        self.fields["password2"].help_text = ""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


# Criação e edição de credenciais.
class VaultItemForm(forms.ModelForm):
    secret = forms.CharField(
        label="Senha", widget=forms.PasswordInput(render_value=True), strip=False
    )
    notes = forms.CharField(
        label="Observações", widget=forms.Textarea(attrs={"rows": 3}), required=False
    )
    shared_with = forms.ModelMultipleChoiceField(
        label="Compartilhar com",
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Selecione um ou mais usuários ativos.",
    )

    class Meta:
        model = VaultItem
        fields = (
            "group",
            "title",
            "host",
            "username",
            "website",
            "secret",
            "notes",
            "visibility",
            "shared_with",
        )
        labels = {"visibility": "Quem pode acessar"}

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        groups = (
            VaultGroup.objects.filter(organization=organization)
            if organization
            else VaultGroup.objects.none()
        )
        self.fields["group"].queryset = groups
        self.fields["shared_with"].queryset = User.objects.filter(
            memberships__organization=organization,
            memberships__is_active=True,
            is_active=True,
        ).exclude(pk=getattr(user, "pk", None))
        if self.instance.pk:
            self.fields["secret"].required = False
            self.fields["secret"].help_text = "Deixe vazio para manter a senha atual."
            self.fields["notes"].initial = self.instance.get_notes()

    def clean(self):
        cleaned = super().clean()
        visibility = cleaned.get("visibility")
        recipients = cleaned.get("shared_with")
        if visibility == VaultItem.Visibility.SPECIFIC and not recipients:
            self.add_error("shared_with", "Selecione pelo menos um usuário.")
        elif visibility != VaultItem.Visibility.SPECIFIC:
            cleaned["shared_with"] = User.objects.none()
        return cleaned

    def save(self, commit=True):
        item = super().save(commit=False)
        if self.cleaned_data.get("secret"):
            item.set_secret(self.cleaned_data["secret"])
        item.set_notes(self.cleaned_data.get("notes", ""))
        if commit:
            item.full_clean()
            item.save()
            self._save_m2m()
        return item


# Criação e edição de grupos.
class VaultGroupForm(forms.ModelForm):
    class Meta:
        model = VaultGroup
        fields = ("name",)
        labels = {"name": "Nome do grupo"}

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = VaultGroup.objects.filter(
            organization=self.organization,
            name__iexact=name,
        ).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("Já existe um grupo com esse nome.")
        return name
