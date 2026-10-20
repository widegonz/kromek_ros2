from setuptools import setup
from glob import glob

package_name = 'kromek_driver'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Research Team',
    maintainer_email='team@example.invalid',
    description='Minimal ROS 2 Foxy driver for Kromek SIGMA50 SDK',
    license='Proprietary',
    entry_points={'console_scripts': ['sigma50_node = kromek_driver.node:main']},
)
