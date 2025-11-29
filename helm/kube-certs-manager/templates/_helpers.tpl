{{/*
Expand the name of the chart.
*/}}
{{- define "kube-certs-manager.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kube-certs-manager.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kube-certs-manager.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kube-certs-manager.labels" -}}
helm.sh/chart: {{ include "kube-certs-manager.chart" . }}
{{ include "kube-certs-manager.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kube-certs-manager.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kube-certs-manager.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kube-certs-manager.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.name }}
{{- .Values.rbac.serviceAccount.name }}
{{- else }}
{{- include "kube-certs-manager.fullname" . }}
{{- end }}
{{- end }}

{{/*
Create the name of the cluster role
*/}}
{{- define "kube-certs-manager.clusterRoleName" -}}
{{- if .Values.rbac.clusterRole.name }}
{{- .Values.rbac.clusterRole.name }}
{{- else }}
{{- include "kube-certs-manager.fullname" . }}
{{- end }}
{{- end }}

{{/*
Create the name of the cluster role binding
*/}}
{{- define "kube-certs-manager.clusterRoleBindingName" -}}
{{- if .Values.rbac.clusterRoleBinding.name }}
{{- .Values.rbac.clusterRoleBinding.name }}
{{- else }}
{{- include "kube-certs-manager.fullname" . }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret
*/}}
{{- define "kube-certs-manager.secretName" -}}
{{- if kindIs "string" .Values.slack.token }}
{{- printf "%s-slack-credentials" (include "kube-certs-manager.fullname" .) }}
{{- else }}
slack-credentials
{{- end }}
{{- end }}

{{/*
Get the namespace
*/}}
{{- define "kube-certs-manager.namespace" -}}
{{- .Values.namespace.name }}
{{- end }}

