pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Test') {
      steps {
        bat 'python install.py --upgrade'
      }
    }
    stage('') {
      steps {
        bat 'python setup.py test'
      }
    }
  }
}