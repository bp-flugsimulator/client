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
      }
    }
  }
}