pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Depndency Install') {
      steps {
        bat 'python install.py'
      }
    }
    stage('Testing') {
      steps {
        bat 'python setup.py test'
      }
    }
  }
}
