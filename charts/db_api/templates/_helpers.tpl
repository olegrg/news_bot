{{/*
Expand the name of the chart.
*/}}
{{- define "db-api.name" -}}
{{ .Chart.Name }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "db-api.fullname" -}}
{{ printf "%s-%s" .Release.Name .Chart.Name }}
{{- end }}
