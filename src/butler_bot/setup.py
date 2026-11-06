
from setuptools import setup
from glob import glob
import os

package_name = 'butler_bot'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
         glob('config/*')),
        (os.path.join('share', package_name, 'maps'),
         glob('maps/*')),
        (os.path.join('share', package_name, 'worlds'),
         glob('worlds/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bharathwaj',
    maintainer_email='bharathwaj@example.com',
    description='ROS 2 autonomous restaurant delivery robot',
    license='MIT',
    entry_points={
        'console_scripts': [
            'butler_manager = butler_bot.butler_task_manager:main',
        ],
    },
)
