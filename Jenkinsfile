pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Test') {
      steps {
        bat 'python manage.py test'
      }
    }
  }
}