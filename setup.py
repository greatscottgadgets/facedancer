from setuptools import setup, find_packages

setup(
   name='facedancer',
   version='2.9',
   description='modern FaceDancer core for multiple devices-- including GreatFET ',
   author='greatscottgadgets',
   author_email='',
   #packages=['facedancer'],  #same as name
   packages=find_packages(),
   install_requires=['pyusb', 'prompt-toolkit'], #external packages as dependencies
)

