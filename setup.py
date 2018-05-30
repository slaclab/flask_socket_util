from setuptools import setup

setup(name='flask_socket_util',
      version='0.0.5',
      description='A small utility for using websockets from within Flask for PSDM web services',
      url='https://github.com/slaclab/flask_socket_util.git',
      author='Murali Shankar',
      author_email='mshankar@slac.stanford.edu',
      license='MIT',
      packages=['flask_socket_util'],
      package_data={'flask_socket_util': ['websocket_client.js']},
      install_requires=['flask >= 1.0.0', 'eventlet >= 0.23.0', 'flask-socketio >= 3.0.0']
      zip_safe=False)
