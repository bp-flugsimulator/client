pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Test') {
      steps {
        bat 'python setup.py test'
      }
    }
  }
}