#!/bin/bash

# curl-model.sh
# Download a specified model from the shared OneDrive models.yaml and place it into backend/python/model/
# Usage: ./curl-models.sh [--help|-h] [-m <model-name>] [--yaml-url <url>]

mkdir -p backend/python/model

if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  echo "Usage: $0 [--help|-h] [-m <model-name>] [--yaml-url <url>]"
  echo ""
  echo "Options:"
  echo "  --help, -h            Show this help message and exit"
  echo "  -m <model-name>       Specify the model to download"
  exit 0
fi
if [ "$1" == "-d" ] && [ -z "$2" ]; then
  echo "Error: -d option requires a dataset name argument."
  exit 1
fi
if [ "$1" == "-d" ] && [ -n "$2" ]; then
  MODEL_NAME="$2"
  MODELS_YAML=$(curl 'https://ueeduph-my.sharepoint.com/personal/concepcion_timothyjames_ue_edu_ph/_layouts/15/download.aspx?SourceUrl=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fmodels%2Fmodels%2Eyaml' \
    -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
    -H 'accept-language: en-US,en;q=0.9' \
    -H 'cookie: MSFPC=GUID=018d8352266641bfa8680659823058c3&HASH=018d&LV=202501&V=4&LU=1738235237094; rtFa=WO9c+3n+GWh27WpR1MWAc691lwh75C0QMpZdz6W4lmImNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxIzEzNDA0NjI3NTY2MDM0NDc3MyM2ZTM4Y2VhMS0zMGQ5LTUwMDAtZWVhOS1hMzJhNWQ2N2VkOGUjY29uY2VwY2lvbi50aW1vdGh5amFtZXMlNDB1ZS5lZHUucGgjMTk2MDEwI2dmYktidWJ6dXRzZ0NseGZpOV9rQ0g0TndYYyNnZmJLYnVienV0c2dDbHhmaTlfa0NINE53WGN12hbsUFZcwVe4kt9Y+KbLDkAxhxEbdXqV77f/cTgWi0mpPfzdODhX2u6rcSyQkn+SLa0yPz9Vbrr5K7utj0ExKH5JNMXftq5gIv9GXhqhmZNLjpj/ICo4hiZ6+J5TnsvjukbDVMRR8dinZscww4yVEvQFii5teYxCvjQTMLRijOXmROavqVtkS7xeWRLNGFHhfRpC1UqaVN2UFGN2OE1jkK+WWxcmNtpa1gHjyPa/Ilhc/4tbRPzmix4RDZfeuFH+yUHjb1wlk+csky0va4ZwzDwNSTFu8Gm+MoPc1xFaH9wQ9No0W1byJB9vh1Uh4y9iHQWHc5W84Mwdyb7YO+hg4AAAAA==; SIMI=eyJzdCI6MH0=; FedAuth=77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjE0LDBoLmZ8bWVtYmVyc2hpcHwxMDAzMjAwMmNmYWFmOTFlQGxpdmUuY29tLDAjLmZ8bWVtYmVyc2hpcHxjb25jZXBjaW9uLnRpbW90aHlqYW1lc0B1ZS5lZHUucGgsMTM0MDA2OTQ2MjcwMDAwMDAwLDEzMzM1NjAyNDQxMDAwMDAwMCwxMzQwNTMxNzc0MjA1MzYyOTksMTM2LjE1OC42MS4xOTgsNjcsNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxLCwwMDdiYzc5OS03YmZmLThjOWQtMTA1Zi04ODIyMTE3NWE5MGEsNmUzOGNlYTEtMzBkOS01MDAwLWVlYTktYTMyYTVkNjdlZDhlLDA1NjkxOWRiLWFhNDQtNDE1ZC1iZGNiLWQ4M2RlNzM0NjViYywsMCwxMzQwNDk3MjE0MjAzODAwNDksMTM0MDUxNDQ5NDIwMzgwMDQ5LCwsZXlKNGJYTmZZMk1pT2lKYlhDSkRVREZjSWwwaUxDSjRiWE5mYzNOdElqb2lNU0lzSW5CeVpXWmxjbkpsWkY5MWMyVnlibUZ0WlNJNkltTnZibU5sY0dOcGIyNHVkR2x0YjNSb2VXcGhiV1Z6UUhWbExtVmtkUzV3YUNJc0luVjBhU0k2SW1FMVVqRjBVbXQwTjJ0eE9GOWhOMGMyTUVoVFFVRWlMQ0poZFhSb1gzUnBiV1VpT2lJeE16UXdNRFk1TkRZeU56QXdNREF3TURBaWZRPT0sMjY1MDQ2Nzc0Mzk5OTk5OTk5OSwxMzQwNDYyNzU2NTAwMDAwMDAsNjgxOGY5ZGYtM2I3Ny00NTI5LWIzMmEtZWI5OTE2M2FmYTU4LCwsLCwsMTE1MjkyMTUwNDYwNjg0Njk3NiwsMTk2MDEwLHJMSFBYbWZOcnlzVVBfZ3hrbzd1VzJoSnRaMCwsbE9IMUxRMGx6N0xXaDhpQlVEVHhtaUNKRWkva1dsYUF0aHN5c0NUOGNtc1UzbWJaUHp2aksrMmcydmdYcmRnY2JSTVZuQlE2eWVBRlhBeXRNdE12cCthTjY4emhaWWtXSktpZ0gvRDQ4dkpXdmlhcnB6NGpORDljL05BV1hVU2tkSXVNZGpNN1RKRDVvMlcvZWdUSHF3WU1yNldlclFZdUk2Q3FoM0lEbW9jV0s5TlVHdzhOQjJocmZ3VWhmVElFNXNpT2Zqb1AyMEU0b1MrWjBzTU1jckdGSlZ2WkZ1N2RPOWRWalh3VDV0U1JrYzY3RkdRVkY0emlzWE5lcVlwRlFZWVNkUzdvSERvc1YwT09reGRYQXJtUHlxOXBxSUs1ZW5BTEFJbkJoQmRQSGNVekJNc2w4TkVOMGI5VjJ5bGNZSGNmRTRVZzRnNUpnRWV1eVNjQ1VnPT08L1NQPg==; FeatureOverrides_experiments=[]; msal.cache.encryption=%7B%22id%22%3A%220199e0bd-8a40-7a6b-b033-ef4c769f16c9%22%2C%22key%22%3A%22acpAjf-HPgY1jf61kD8KZsiejN93RIjxeNX6WAupiN0%22%7D; MicrosoftApplicationsTelemetryDeviceId=e14efdc5-7293-45f2-abc2-2aa4e37f9b81; ai_session=FYu8U2tUzQ27PSEmB1XVic|1760417850113|1760417937991; SPA_RT=' \
    -H 'dnt: 1' \
    -H 'if-none-match: "{7FCD17FC-8B95-4338-BF63-1064EF32A21A},11"' \
    -H 'priority: u=0, i' \
    -H 'referer: https://ueeduph-my.sharepoint.com/my?id=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fmodels%2Fmodels%2Eyaml&parent=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fmodels&ga=1' \
    -H 'sec-ch-ua: "Not?A_Brand";v="99", "Chromium";v="130"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "Windows"' \
    -H 'sec-fetch-dest: iframe' \
    -H 'sec-fetch-mode: navigate' \
    -H 'sec-fetch-site: same-origin' \
    -H 'sec-fetch-user: ?1' \
    -H 'sec-gpc: 1' \
    -H 'service-worker-navigation-preload: {"supportsFeatures":[1855,61313,62475]}' \
    -H 'upgrade-insecure-requests: 1' \
    -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
  )
    
  echo "$MODELS_YAML"

  # Extract the curl_bash block for the model
  CURL_CMD=$(echo "$MODELS_YAML" | awk -v name="$MODEL_NAME" '
    BEGIN { in_block=0; in_curl=0 }
    /- name:/ {
      # Check if this line contains our model name
      if ($0 ~ name) {
        in_block=1
      } else {
        in_block=0
        in_curl=0
      }
    }
    in_block && /curl_bash:/ {
      in_curl=1
      next
    }
    in_curl {
      # Stop if we hit another top-level key (description, etc) at same indent level as curl_bash
      if (/^    [a-z_]+:/ && !/^      /) {
        exit
      }
      # Stop if we hit another dataset entry
      if (/^  - name:/) {
        exit
      }
      # Print the curl command lines (they start with 6 spaces)
      if (/^      / && NF > 0) {
        gsub(/^      /, "")
        print
      }
    }
  ')

  if [ -z "$CURL_CMD" ]; then
    echo "Error: Model '$MODEL_NAME' not found or does not have a curl_bash command."
    exit 1
  fi

  # Add --output flag if not already present
  if [[ "$CURL_CMD" != *"--output"* ]] && [[ "$CURL_CMD" != *"-o "* ]]; then
    # Find the position to insert --output (before any URL that starts with http)
    # This ensures --output comes before the URL
    CURL_CMD="curl --output backend/python/model/$MODEL_NAME ${CURL_CMD#curl }"
  fi

  echo "Downloading model '$MODEL_NAME'..."
  echo "Executing: $CURL_CMD"
  eval "$CURL_CMD"

  # Unzip and cleanup
  if [ -f "backend/python/model/$MODEL_NAME" ]; then
    echo "Model '$MODEL_NAME' downloaded and extracted successfully."
  else
    echo "Error: Model file 'backend/python/model/$MODEL_NAME' was not downloaded."
    exit 1
  fi

  exit 0
fi