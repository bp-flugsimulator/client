pipeline {
  agent {
    node {
      label 'windows'
    }
    
  }
  stages {
    stage('Depndency Install') {
      steps {
        bat 'python -m pip uninstall psutil -y'
        bat 'python install.py --upgrade'
      }
    }
    stage('Testing') {
      steps {
        bat 'python setup.py test'
      }
    }
  }
}
