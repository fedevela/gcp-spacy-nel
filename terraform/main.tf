provider "google" {
  project = "federicoveladataartcomproject"
  region  = "us-central1"
}

# Create the GCR (Google Container Registry)
resource "google_container_registry" "registry" {}

# Set up a Cloud Run service
resource "google_cloud_run_service" "spacy_nel_service" {
  name     = "spacy-nel"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "gcr.io/federicoveladataartcomproject/spacy-nel:v1"
        ports {
          container_port = 8080
        }
        resources {
          limits = {
            memory = "2048Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true
}

# Allow unauthenticated access to the Cloud Run service
resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_service.spacy_nel_service.location
  project     = google_cloud_run_service.spacy_nel_service.project
  service     = google_cloud_run_service.spacy_nel_service.name
  policy_data = data.google_iam_policy.noauth.policy_data
}

data "google_iam_policy" "noauth" {
  binding {
    role    = "roles/run.invoker"
    members = ["allUsers"]
  }
}
