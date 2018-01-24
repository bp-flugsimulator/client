pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Test') {
      steps {
        sh 'python setup.py test'
        bat 'python manage.py test'
      }
    }
  }
}